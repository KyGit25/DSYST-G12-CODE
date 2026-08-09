import os
import requests

# ==========================================
# Utility Functions
# ==========================================

def pause():
    input("\nPress ENTER to continue...")


def line():
    print("=" * 90)


def print_logs(data):

    results = data.get("results", [])

    if len(results) == 0:
        print("\nNo matching logs found.\n")
        return

    print(f"\nFound {len(results)} matching logs.\n")

    print(
        f"{'Timestamp':<18}"
        f"{'Hostname':<18}"
        f"{'Daemon':<18}"
        f"{'Severity':<12}"
        f"Message"
    )

    print("-" * 90)

    for log in results:

        print(
            f"{log['timestamp']:<18}"
            f"{log['hostname']:<18}"
            f"{log['daemon']:<18}"
            f"{log['severity']:<12}"
            f"{log['message']}"
        )


def request_error(e):

    print("\nUnable to connect to Gateway.")
    print("Reason:", e)

    pause()


# ==========================================
# INGEST
# ==========================================

def ingest():

    line()
    print("INGEST LOG FILE")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    filepath = input(
        "\nLog File Path\n"
        "Example: sample.log\n> "
    ).strip()

    if not os.path.exists(filepath):

        print("\nFile not found.")

        pause()

        return

    try:

        with open(filepath, "rb") as file:

            response = requests.post(
                f"http://{gateway}:8000/ingest",
                files={"file": file}
            )

        data = response.json()

        print("\nUpload Successful!")

        print(f"Logs Uploaded : {data['logs_received']}")

    except Exception as e:

        request_error(e)

        return

    pause()


# ==========================================
# PURGE
# ==========================================

def purge():

    line()
    print("PURGE DATABASE")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    confirm = input(
        "\nType YES to continue: "
    )

    if confirm != "YES":

        print("\nOperation Cancelled.")

        pause()

        return

    try:

        response = requests.delete(
            f"http://{gateway}:8000/purge"
        )

        data = response.json()

        print("\nDatabase Cleared Successfully.")

        print(f"Deleted Logs : {data['deleted']}")

    except Exception as e:

        request_error(e)

        return

    pause()
# ==========================================
# SEARCH FUNCTIONS
# ==========================================

def search_date():

    line()
    print("SEARCH DATE")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    date = input(
        "\nDate String\n"
        "Example: Mar 12\n> "
    ).strip()

    try:

        response = requests.get(
            f"http://{gateway}:8000/search/date",
            params={"date": date}
        )

        print_logs(response.json())

    except Exception as e:

        request_error(e)
        return

    pause()


def search_host():

    line()
    print("SEARCH HOST")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    hostname = input(
        "\nHostname\n"
        "Example: WEB-SRV-01\n> "
    ).strip()

    try:

        response = requests.get(
            f"http://{gateway}:8000/search/host",
            params={"hostname": hostname}
        )

        print_logs(response.json())

    except Exception as e:

        request_error(e)
        return

    pause()


def search_daemon():

    line()
    print("SEARCH DAEMON")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    daemon = input(
        "\nDaemon Name\n"
        "Example: apache2\n> "
    ).strip()

    try:

        response = requests.get(
            f"http://{gateway}:8000/search/daemon",
            params={"daemon": daemon}
        )

        print_logs(response.json())

    except Exception as e:

        request_error(e)
        return

    pause()


def search_severity():

    line()
    print("SEARCH SEVERITY")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    severity = input(
        "\nSeverity Level\n"
        "Example: ERROR\n> "
    ).strip().upper()

    try:

        response = requests.get(
            f"http://{gateway}:8000/search/severity",
            params={"severity": severity}
        )

        print_logs(response.json())

    except Exception as e:

        request_error(e)
        return

    pause()


def search_keyword():

    line()
    print("SEARCH KEYWORD")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    keyword = input(
        "\nKeyword\n"
        "Example: failed\n> "
    ).strip()

    try:

        response = requests.get(
            f"http://{gateway}:8000/search/keyword",
            params={"keyword": keyword}
        )

        print_logs(response.json())

    except Exception as e:

        request_error(e)
        return

    pause()


def count_keyword():

    line()
    print("COUNT KEYWORD")
    line()

    gateway = input(
        "\nGateway IP\n"
        "Example: localhost\n> "
    ).strip()

    keyword = input(
        "\nKeyword\n"
        "Example: failed\n> "
    ).strip()

    try:

        response = requests.get(
            f"http://{gateway}:8000/count/keyword",
            params={"keyword": keyword}
        )

        data = response.json()

        print("\nResult")
        print("-" * 25)
        print(f"Keyword : {data['keyword']}")
        print(f"Count   : {data['count']}")

    except Exception as e:

        request_error(e)
        return

    pause()


# ==========================================
# QUERY MENU
# ==========================================

def query_menu():

    while True:

        line()
        print("QUERY MENU")
        line()

        print("""
1. SEARCH DATE
2. SEARCH HOST
3. SEARCH DAEMON
4. SEARCH SEVERITY
5. SEARCH KEYWORD
6. COUNT KEYWORD
7. BACK
""")

        choice = input("Enter Choice: ").strip()

        if choice == "1":
            search_date()

        elif choice == "2":
            search_host()

        elif choice == "3":
            search_daemon()

        elif choice == "4":
            search_severity()

        elif choice == "5":
            search_keyword()

        elif choice == "6":
            count_keyword()

        elif choice == "7":
            break

        else:
            print("\nInvalid Choice.")
            pause()


# ==========================================
# MAIN MENU
# ==========================================

def main():

    while True:

        line()
        print("MiniSplunk Forwarder")
        line()

        print("""
1. INGEST
2. QUERY
3. PURGE
4. EXIT
""")

        choice = input("Enter Choice: ").strip()

        if choice == "1":
            ingest()

        elif choice == "2":
            query_menu()

        elif choice == "3":
            purge()

        elif choice == "4":

            print("\nThank you for using MiniSplunk.")
            break

        else:

            print("\nInvalid Choice.")
            pause()


if __name__ == "__main__":
    main()
