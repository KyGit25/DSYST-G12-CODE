import time
import pika
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError, ServerSelectionTimeoutError

from parser import parse_log

credentials = pika.PlainCredentials("rabbituser", "rabbit1234")

connection = None
while connection is None:
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="rabbitmq", credentials=credentials)
        )
        print("Connected to RabbitMQ")
    except pika.exceptions.AMQPConnectionError:
        print("RabbitMQ not ready... retrying in 5 seconds")
        time.sleep(5)

channel = connection.channel()
channel.queue_declare(queue="log_queue", durable=True)
channel.basic_qos(prefetch_count=1)

# -----------------------
# Connect to MongoDB
# -----------------------

mongo = None
while mongo is None:
    try:
        mongo = MongoClient("mongodb://mongos:27017/", serverSelectionTimeoutMS=5000)
        mongo.admin.command("ping")
        print("Connected to MongoDB")
    except ServerSelectionTimeoutError:
        print("MongoDB not ready... retrying in 5 seconds")
        time.sleep(5)

db = mongo["minisplunk"]
collection = db["logs"]
locks_collection = db["locks"]

PURGE_LOCK_ID = "purge_lock"

# -----------------------
# Callback
# -----------------------

def callback(ch, method, properties, body):
    log = body.decode()
    parsed = parse_log(log)

    if parsed is None:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    if locks_collection.find_one({"_id": PURGE_LOCK_ID}):
        # a purge is running right now, do not write. Put the message back
        # on the queue so it is processed again once the purge is done.
        print("Purge in progress, requeueing message")
        time.sleep(1)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return

    # parse the message's own id as the MongoDB _id, so a message that gets
    # redelivered can't be stored twice
    parsed["_id"] = properties.message_id

    try:
        collection.insert_one(parsed)
        print("Stored log:", parsed)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except DuplicateKeyError:
        print("Already stored, skipping duplicate:", parsed["_id"])
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except PyMongoError as e:
        print("Mongo error:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# -----------------------
# Start Consumer
# -----------------------

channel.basic_consume(queue="log_queue", on_message_callback=callback)
print("Worker waiting for logs...")
channel.start_consuming()
