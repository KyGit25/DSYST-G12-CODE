import re

SYSLOG_REGEX = re.compile(
    r'^(?:<(?P<priority>\d+)>)?'
    r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<daemon>[^:]+):\s*'
    r'(?P<message>.+)$'
)

# RFC3164 syslog priority codes: the last 3 bits of the PRI number are the
# severity level (0 = most severe, 7 = least severe). We map the 8 levels
# down to the 3 severities this project uses.
PRIORITY_TO_SEVERITY = {
    0: "ERROR",    # Emergency
    1: "ERROR",    # Alert
    2: "ERROR",    # Critical
    3: "ERROR",    # Error
    4: "WARNING",  # Warning
    5: "INFO",     # Notice
    6: "INFO",     # Informational
    7: "INFO",     # Debug
}


def severity_from_priority(priority):
    severity_code = int(priority) % 8
    return PRIORITY_TO_SEVERITY[severity_code]


def severity_from_keywords(message):
    message = message.lower()

    if "error" in message or "failed" in message or "denied" in message:
        return "ERROR"
    elif "warn" in message or "warning" in message:
        return "WARNING"
    else:
        return "INFO"


def parse_log(log):
    match = SYSLOG_REGEX.match(log.strip())

    if not match:
        return None

    data = match.groupdict()
    priority = data.pop("priority")

    if priority is not None:
        # the log line had a real "<PRI>" code, so use that
        data["severity"] = severity_from_priority(priority)
    else:
        # no priority code, fall back to guessing from the message text
        data["severity"] = severity_from_keywords(data["message"])

    return data
