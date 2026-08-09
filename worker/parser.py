import re

SYSLOG_REGEX = re.compile(
    r'^(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<daemon>[\w\-\./]+(?:\[\d+\])?):\s+'
    r'(?P<message>.*)$'
)


def parse_log(log):

    match = SYSLOG_REGEX.match(log)

    if not match:
        return None

    data = match.groupdict()

    message = data["message"].lower()

    if "error" in message:
        severity = "ERROR"

    elif "warn" in message:
        severity = "WARNING"

    else:
        severity = "INFO"

    data["severity"] = severity

    return data
