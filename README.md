# Distributed Mini-Splunk Log Analytics Ecosystem - Implementation Guide

## Overview

This project implements a lightweight distributed log analytics ecosystem inspired by Splunk.

Instead of using a centralized server, the system is decomposed into multiple independent services communicating through REST APIs and RabbitMQ. The architecture enables asynchronous log ingestion, distributed parsing, scalable storage, and fault-tolerant search operations.

The system consists of the following components:

- **Forwarder (forwarder.py)** – Command-line client that uploads syslog files and submits search requests.
- **API Gateway (gateway.py)** – Single entry point that receives client requests, publishes ingestion jobs to RabbitMQ, coordinates distributed searches, and returns aggregated results.
- **RabbitMQ Message Broker** – Inter-process communication (IPC) middleware responsible for asynchronous workload distribution.
- **Worker Nodes (worker.py)** – Multiple containerized workers that consume log messages, parse RFC3164 syslog entries, and insert structured documents into MongoDB.
- **MongoDB Sharded Cluster** – Distributed storage layer consisting of multiple shards accessed through a Mongo Router (mongos).

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
SYSLOG_PATTERN = re.compile(
    r'^(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<daemon>\S+):\s+'
    r'(?P<message>.*)$'
)
```

Extracted fields

- timestamp
- hostname
- daemon
- severity
- message

Severity is inferred from keywords or priority fields.

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

Used during PURGE

1. Acquire distributed lock
2. Suspend worker writes
3. Clear database shards
4. Release lock

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
gateway

rabbitmq

worker1

worker2

mongos

mongo-config

mongo-shard1

mongo-shard2
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

## Upload Logs

```bash
python forwarder.py INGEST syslog.log http://localhost:8000
```

---

## Search by Host

```bash
python forwarder.py QUERY SEARCH_HOST server01
```

---

## Search by Severity

```bash
python forwarder.py QUERY SEARCH_SEVERITY ERROR
```

---

## Count Keyword

```bash
python forwarder.py QUERY COUNT_KEYWORD ERROR
```

---

## Purge Logs

```bash
python forwarder.py PURGE
```

---

# Chaos Testing

Start ingestion

```bash
python forwarder.py INGEST large_syslog.log
```

While processing

```bash
docker stop worker2
```

Expected

- RabbitMQ requeues unfinished jobs
- Worker1 continues processing
- No missing log entries
- No duplicate log entries

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
