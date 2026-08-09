from fastapi import FastAPI, UploadFile, File
import pika
from pymongo import MongoClient

app = FastAPI()

RABBITMQ_HOST = "rabbitmq"
mongo = MongoClient("mongodb://mongos:27017/")

db = mongo["minisplunk"]

collection = db["logs"]

@app.get("/")
def home():
    return {"message": "MiniSplunk Gateway Running"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):

    credentials = pika.PlainCredentials(
        "rabbituser",
        "rabbit1234"
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials
        )
    )

    channel = connection.channel()
    channel.queue_declare(
	queue="log_queue",
	durable=True
    )

    contents = await file.read()
    logs = contents.decode().splitlines()

    for log in logs:
        channel.basic_publish(
            exchange="",
            routing_key="log_queue",
            body=log
        )

    connection.close()

    return {
        "status": "success",
        "logs_received": len(logs)
    }
@app.get("/search/host")
def search_host(hostname: str):

    results = list(
        collection.find(
            {"hostname": hostname},
            {"_id": 0}
        )
    )

    return {
        "count": len(results),
        "results": results
    }
@app.get("/search/date")
def search_date(date: str):

    results = list(
        collection.find(
            {"timestamp": {"$regex": f"^{date}"}},
            {"_id": 0}
        )
    )

    return {
        "count": len(results),
        "results": results
    }
@app.get("/search/daemon")
def search_daemon(daemon: str):

    results = list(
        collection.find(
            {"daemon": daemon},
            {"_id": 0}
        )
    )

    return {
        "count": len(results),
        "results": results
    }
@app.get("/search/severity")
def search_severity(severity: str):

    results = list(
        collection.find(
            {"severity": severity.upper()},
            {"_id": 0}
        )
    )

    return {
        "count": len(results),
        "results": results
    }
@app.get("/search/keyword")
def search_keyword(keyword: str):

    results = list(
        collection.find(
            {
                "message": {
                    "$regex": keyword,
                    "$options": "i"
                }
            },
            {"_id": 0}
        )
    )

    return {
        "count": len(results),
        "results": results
    }
@app.get("/count/keyword")
def count_keyword(keyword: str):

    count = collection.count_documents(
        {
            "message": {
                "$regex": keyword,
                "$options": "i"
            }
        }
    )

    return {
        "keyword": keyword,
        "count": count
    }
@app.delete("/purge")
def purge():

    result = collection.delete_many({})

    return {
        "status": "success",
        "deleted": result.deleted_count
    }

