# Distributed Mini-Splunk Log Analytics Ecosystem - Implementation Guide

## Overview

This project implements a lightweight distributed log analytics ecosystem inspired by Splunk.

Instead of using a centralized server, the system is decomposed into multiple independent services communicating through REST APIs and RabbitMQ. The architecture enables asynchronous log ingestion, distributed parsing, scalable storage, and fault-tolerant search operations.

The system consists of the following components:

- **Forwarder (forwarder/forwarder.py)** – Interactive command-line client that uploads syslog files and submits search/purge requests.
- **API Gateway (gateway/app.py)** – Single entry point that receives client requests, publishes ingestion jobs to RabbitMQ, coordinates distributed searches, and returns aggregated results.
- **RabbitMQ Message Broker** – Inter-process communication (IPC) middleware responsible for asynchronous workload distribution.
- **Worker Nodes (worker/worker.py)** – Multiple containerized workers that consume log messages, parse RFC3164 syslog entries, and insert structured documents into MongoDB.
- **MongoDB Sharded Cluster** – Distributed storage layer consisting of a config server replica set and two shard replica sets, accessed through a Mongo Router (mongos), all bootstrapped automatically by `scripts/init-sharding.sh`.

---

# Architecture

## Distributed Server Architecture

```
CLI Forwarder
        │
        │ REST API
        ▼
+----------------------+
|   API Gateway        |
|  (Search Head)       |
+----------+-----------+
           │
           │ Publish Jobs
           ▼
+----------------------+
|      RabbitMQ        |
| Message Queue (IPC)  |
+-----+-----------+----+
      │           │
      │           │
      ▼           ▼
+-----------+ +-----------+
| Worker 1  | | Worker 2  |
+-----------+ +-----------+
      │           │
      └─────┬─────┘
            ▼
      Mongo Router
        (mongos)
            │
     ┌──────┴──────┐
     ▼             ▼
Mongo Shard1   Mongo Shard2
```

Each service executes a single responsibility and communicates only through defined interfaces, enabling loose coupling and independent scalability.

---

## Functional Decomposition

### Forwarder

Responsibilities

- Reads local syslog files
- Sends REST requests to API Gateway
- Displays search results

---

### API Gateway

Responsibilities

- Accepts all client requests
- Validates requests
- Publishes logs into RabbitMQ
- Coordinates distributed queries
- Aggregates search results
- Coordinates PURGE operations

---

### RabbitMQ

Responsibilities

- Provides asynchronous communication
- Buffers uploaded logs
- Load balances work among workers
- Automatically redistributes unfinished jobs

---

### Worker Nodes

Responsibilities

- Consume queue messages
- Parse RFC3164 syslog entries
- Extract log fields
- Store structured documents

---

### MongoDB Sharded Cluster

Responsibilities

- Distributed storage
- High availability
- Scatter-gather searching
- Horizontal scalability

---

# Communication Model

The system utilizes two communication mechanisms.

## REST API

Used between

```
Forwarder

↓

Gateway
```

Functions

- INGEST
- QUERY
- PURGE

---

## RabbitMQ

Used between

```
Gateway

↓

Workers
```

Functions

- Queue management
- Asynchronous processing
- Load balancing
- Reliable message delivery

---

# Log Parsing

Worker Nodes parse each RFC3164 syslog entry using regular expressions.

Example pattern

```python
SYSLOG_REGEX = re.compile(
    r'^(?:<(?P<priority>\d+)>)?'
    r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<daemon>[^:]+):\s*'
    r'(?P<message>.+)$'
)
```

Extracted fields

- timestamp
- hostname
- daemon
- severity
- message

Severity is derived in one of two ways:

1. **Real syslog priority code (RFC3164 PRI)** – if the log line has a `<PRI>` prefix (e.g. `<34>`), the severity is decoded from it: `severity_code = PRI % 8`, then mapped down to this project's three-level scheme (`ERROR` for Emergency/Alert/Critical/Error, `WARNING` for Warning, `INFO` for Notice/Informational/Debug).
2. **Keyword fallback** – if there is no `<PRI>` prefix, severity is guessed from the message text (`"error"`, `"failed"`, `"denied"` → `ERROR`; `"warn"`/`"warning"` → `WARNING`; otherwise `INFO`).

See `worker/parser.py` for the implementation.

---

# MongoDB Data Layout

Each parsed log is stored as a document.

```json
{
    "timestamp": "Mar 12 05:26:34",
    "hostname": "WEB-SRV-01",
    "daemon": "apache2",
    "severity": "ERROR",
    "message": "failed to open stream: No such file or directory"
}
```

Documents are automatically distributed among MongoDB shards through the Mongo Router.

---

# Client–Server Communication

| Command | REST Endpoint | Gateway Action |
|----------|--------------|----------------|
| INGEST | POST /ingest | Uploads file, splits logs, publishes each log into RabbitMQ |
| SEARCH_DATE | GET /search/date | Scatter-gather query across shards |
| SEARCH_HOST | GET /search/host | Queries hostname field |
| SEARCH_DAEMON | GET /search/daemon | Queries daemon field |
| SEARCH_SEVERITY | GET /search/severity | Queries severity field |
| SEARCH_KEYWORD | GET /search/keyword | Searches message contents |
| COUNT_KEYWORD | GET /count/keyword | Aggregates counts from every shard |
| PURGE | DELETE /purge | Acquires distributed lock and clears every shard |

---

# Gateway Implementation

### Upload Module

- Accepts uploaded syslog files
- Splits logs into individual messages
- Publishes each message to RabbitMQ

---

### Query Coordinator

- Receives search requests
- Executes scatter-gather search
- Merges results
- Returns formatted responses

---

### Distributed Lock Manager

Used during PURGE. The lock lives in MongoDB itself (a `locks` collection, separate from `logs`), so it works correctly even with multiple gateway instances since `_id` values are guaranteed unique cluster-wide.

1. Gateway tries to `insert_one({"_id": "purge_lock"})` into the `locks` collection.
   - If it succeeds, the lock is acquired.
   - If it fails with a duplicate key error, a purge is already running and the request is rejected with HTTP 423.
2. While the lock document exists, any worker that is about to insert a parsed log first checks for it. If it's there, the worker `nack`s the message (put it back on the queue) instead of writing — this is what "suspends worker writes."
3. Gateway clears the `logs` collection (`delete_many({})`).
4. Gateway deletes the lock document, releasing it (this always runs, even if the delete fails, via `try/finally`).

See `purge()` in `gateway/app.py` and the lock check inside `callback()` in `worker/worker.py`.

---

# Worker Implementation

Each worker performs

1. Consume RabbitMQ message
2. Parse syslog entry
3. Validate fields
4. Insert document into MongoDB
5. Acknowledge RabbitMQ message

Workers remain stateless and may be scaled horizontally.

---

# Fault Tolerance

RabbitMQ acknowledgements provide reliable message processing.

```
Worker

↓

Receive Message

↓

Insert MongoDB

↓

ACK
```

If a worker crashes before ACK

```
RabbitMQ

↓

Message Requeued

↓

Another Worker

↓

Processing Continues
```

Result

- Zero message loss
- Zero duplicate processing
- Autonomous recovery

---

# Deployment

The entire ecosystem is deployed using Docker Compose.

Containers

```
rabbitmq

configsvr      (Mongo config server replica set)

shard1         (Mongo shard 1 replica set)

shard2         (Mongo shard 2 replica set)

mongos         (Mongo router)

mongo-init     (one-shot container that runs scripts/init-sharding.sh,
                then exits — gateway/worker1/worker2 wait for it to
                finish successfully before they start)

gateway

worker1

worker2

forwarder
```

Deployment

```bash
docker compose up -d
```

Shutdown

```bash
docker compose down
```

---

# Usage

## Start the Ecosystem

```bash
docker compose up -d
```

---

## Run the Forwarder

The forwarder is an interactive, menu-driven CLI, not a command-line-args tool. It already runs as its own container (`stdin_open`/`tty` are enabled in `docker-compose.yml`), so attach to it directly:

```bash
docker attach forwarder
```

You'll see a menu:

```
1. INGEST
2. QUERY
3. PURGE
4. EXIT
```

Each option then prompts you for the Gateway IP (e.g. `localhost` or `gateway` if you're inside the Docker network), a file path (for INGEST), or search terms (for QUERY). Detach without stopping the container with `Ctrl+P` then `Ctrl+Q`.

Alternatively, run it locally on your host (outside Docker) once `pip install -r forwarder/requirements.txt` is done:

```bash
python forwarder/forwarder.py
```

---

# Chaos Testing

`scripts/chaos_test.py` automates the fault-tolerance test end to end. It:

1. Clears the `logs` collection so the count check is exact.
2. Uploads 50 generated log lines through `/ingest`.
3. Immediately runs `docker kill worker1` (a hard, forceful kill, not a graceful stop) while messages are likely still being processed, then `docker start worker1` to bring it back.
4. Polls the document count in MongoDB and fails loudly if it's ever less than 50 (data loss) or more than 50 (duplicate processing).

Run it (with the ecosystem already up):

```bash
python -m pip install pymongo
python scripts/chaos_test.py
```

Expected result

```
Chaos test passed: no data loss or duplicate insertion detected
```

This works because RabbitMQ only removes a message from the queue once a worker explicitly acknowledges it (`ch.basic_ack`, in `worker/worker.py`). If `worker1` is killed before it acks a message, RabbitMQ redelivers that message to `worker2` once the connection drops — so no message is lost, and `worker2` (not a still-alive `worker1`) picks up the slack.

---

# Scalability

Additional worker nodes may be added without modifying application logic.

Example

```
worker1

worker2

worker3

worker4
```

RabbitMQ automatically distributes incoming log messages among available workers.

---
