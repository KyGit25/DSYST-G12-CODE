import re

SYSLOG_REGEX = re.compile(
    r'^(?:<(?P<priority>\d+)>)?'
    r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<hostname>\S+)\s+'
    r'(?P<daemon>[^:]+):\s*'
    r'(?P<message>.+)$'
)

PRIORITY_TO_SEVERITY = {
    0: "ERROR",    
    1: "ERROR",    
    2: "ERROR",    
    3: "ERROR",    
    4: "WARNING", 
    5: "INFO",     
    6: "INFO",   
    7: "INFO",    
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
        data["severity"] = severity_from_priority(priority)
    else:
        data["severity"] = severity_from_keywords(data["message"])

    return data
