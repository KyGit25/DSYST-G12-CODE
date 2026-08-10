import uuid
import pika
from fastapi import FastAPI, File, HTTPException, UploadFile
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

app = FastAPI()

RABBITMQ_HOST = "rabbitmq"
MONGO_HOST = "mongos"

mongo = MongoClient(f"mongodb://{MONGO_HOST}:27017/")
db = mongo["minisplunk"]
collection = db["logs"]
locks_collection = db["locks"]

PURGE_LOCK_ID = "purge_lock"


@app.get("/")
def home():
    return {"message": "MiniSplunk Gateway Running"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    try:
        contents = await file.read()
        logs = [line for line in contents.decode().splitlines() if line.strip()]

        if not logs:
            raise HTTPException(status_code=400, detail="The file has no log lines")

        credentials = pika.PlainCredentials("rabbituser", "rabbit1234")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        channel.queue_declare(queue="log_queue", durable=True)

        for log in logs:
            # give every message its own unique id 
            channel.basic_publish(
                exchange="",
                routing_key="log_queue",
                body=log,
                properties=pika.BasicProperties(message_id=str(uuid.uuid4())),
            )

        connection.close()

        return {"status": "success", "logs_received": len(logs)}
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The file is not valid text") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/search/host")
def search_host(hostname: str):
    results = list(collection.find({"hostname": hostname}, {"_id": 0}))
    return {"count": len(results), "results": results}


@app.get("/search/date")
def search_date(date: str):
    results = list(collection.find({"timestamp": {"$regex": f"^{date}"}}, {"_id": 0}))
    return {"count": len(results), "results": results}


@app.get("/search/daemon")
def search_daemon(daemon: str):
    results = list(collection.find({"daemon": daemon}, {"_id": 0}))
    return {"count": len(results), "results": results}


@app.get("/search/severity")
def search_severity(severity: str):
    results = list(collection.find({"severity": severity.upper()}, {"_id": 0}))
    return {"count": len(results), "results": results}


@app.get("/search/keyword")
def search_keyword(keyword: str):
    results = list(collection.find({"message": {"$regex": keyword, "$options": "i"}}, {"_id": 0}))
    return {"count": len(results), "results": results}


@app.get("/count/keyword")
def count_keyword(keyword: str):
    count = collection.count_documents({"message": {"$regex": keyword, "$options": "i"}})
    return {"keyword": keyword, "count": count}


@app.delete("/purge")
def purge():
    try:
        locks_collection.insert_one({"_id": PURGE_LOCK_ID})
    except DuplicateKeyError:
        raise HTTPException(status_code=423, detail="Purge is already in progress, try again later")

    try:
        result = collection.delete_many({})
    finally:
        # always release the lock, even if the delete fails
        locks_collection.delete_one({"_id": PURGE_LOCK_ID})

    return {"status": "success", "deleted": result.deleted_count}

