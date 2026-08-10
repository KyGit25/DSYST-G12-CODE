import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    from pymongo import MongoClient
except ImportError as exc:
    raise SystemExit("pymongo is required. Install it with: python -m pip install pymongo") from exc

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")


def run(cmd):
    return subprocess.run(cmd, cwd=str(ROOT), check=True, capture_output=True, text=True)


def upload_sample_logs(num_lines=50):
    temp_file = ROOT / "chaos_test.log"
    lines = []
    for i in range(num_lines):
        lines.append(f"<34>Mar 12 05:26:{i % 60:02d} WEB-SRV-01 apache2: ERROR test log line {i}")
    temp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    boundary = "----MiniSplunkBoundary"
    body = []
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="file"; filename="chaos_test.log"\r\nContent-Type: text/plain\r\n\r\n')
    body.append(temp_file.read_bytes())
    body.append(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{GATEWAY_URL}/ingest",
        data=b"".join(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode()


def count_documents(client):
    db = client["minisplunk"]
    return db["logs"].count_documents({})


def main():
    print("Starting chaos test")
    run(["docker", "compose", "-f", str(COMPOSE_FILE), "ps"])

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)

    # start from a clean slate so the counts below are exact
    client["minisplunk"]["logs"].delete_many({})

    expected_count = 50
    upload_sample_logs(expected_count)

    # kill worker1 right away, while it is likely still processing messages
    # from the queue, to simulate the "kill a worker mid-ingestion" scenario
    print("Killing worker1 mid-ingestion...")
    run(["docker", "kill", "worker1"])
    run(["docker", "start", "worker1"])

    final_count = 0
    for _ in range(30):
        final_count = count_documents(client)
        if final_count >= expected_count:
            break
        time.sleep(2)

    print(f"Expected document count: {expected_count}")
    print(f"Final document count: {final_count}")

    if final_count < expected_count:
        raise SystemExit("Data loss detected: fewer documents than expected")

    if final_count > expected_count:
        raise SystemExit("Duplicate documents detected")

    print("Chaos test passed: no data loss or duplicate insertion detected")


if __name__ == "__main__":
    main()
