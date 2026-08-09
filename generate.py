import random

daemons = [
    "apache2",
    "sshd",
    "nginx",
    "mysql",
    "postfix",
    "docker",
    "kernel"
]

severities = [
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]

messages = [
    "User login successful",
    "Failed password attempt",
    "Connection timed out",
    "Disk usage exceeded threshold",
    "Service restarted",
    "Permission denied",
    "Database connection lost",
    "HTTP request completed",
    "Segmentation fault detected",
    "Memory usage high"
]

with open("manylogs.log", "w") as f:
    for i in range(1, 100001):

        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        daemon = random.choice(daemons)
        severity = random.choice(severities)
        message = random.choice(messages)

        line = (
            f"Mar {day:02d} "
            f"{hour:02d}:{minute:02d}:{second:02d} "
            f"WEB-SRV-{i:02d} "
            f"{daemon}: "
            f"{severity} {message}\n"
        )

        f.write(line)

print("Generated 100000  logs in manylogs.log")
