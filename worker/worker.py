import time
import pika

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError

from parser import parse_log

# -----------------------
# RabbitMQ Credentials
# -----------------------

credentials = pika.PlainCredentials(
    "rabbituser",
    "rabbit1234"
)

# -----------------------
# Connect to RabbitMQ
# -----------------------

connection = None

while connection is None:
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host="rabbitmq",
                credentials=credentials
            )
        )

        print("Connected to RabbitMQ!")

    except pika.exceptions.AMQPConnectionError:
        print("RabbitMQ not ready... retrying in 5 seconds")
        time.sleep(5)

channel = connection.channel()

channel.queue_declare(
    queue="log_queue",
    durable=True
)

channel.basic_qos(prefetch_count=1)

# -----------------------
# Connect to MongoDB
# -----------------------

mongo = None

while mongo is None:
    try:
        mongo = MongoClient(
            "mongodb://mongos:27017/",
            serverSelectionTimeoutMS=5000
        )

        mongo.admin.command("ping")

        print("Connected to MongoDB!")

    except ServerSelectionTimeoutError:
        print("MongoDB not ready... retrying in 5 seconds")
        time.sleep(5)

db = mongo["minisplunk"]
collection = db["logs"]

# -----------------------
# Callback
# -----------------------

def callback(ch, method, properties, body):

    log = body.decode()

    parsed = parse_log(log)

    if parsed:
        try:

            collection.insert_one(parsed)

            print("\n===== STORED =====")
            print(parsed)

            ch.basic_ack(
                delivery_tag=method.delivery_tag
            )

        except PyMongoError as e:

            print(f"MongoDB Error: {e}")

            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True
            )

# -----------------------
# Start Consumer
# -----------------------

channel.basic_consume(
    queue="log_queue",
    on_message_callback=callback
)

print("Worker waiting for logs...")

channel.start_consuming()
