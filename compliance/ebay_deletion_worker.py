"""Worker mínimo para ejecutar junto al proceso WSGI."""

import os
import time

from compliance.ebay_deletion_wsgi import process_deletions_from_env


def main():
    interval = max(1, int(os.getenv("EBAY_DELETION_WORKER_INTERVAL_SECONDS", "5")))
    while True:
        try:
            process_deletions_from_env()
        except Exception:
            # No incluir payloads ni identificadores en logs. La tarea queda pendiente.
            pass
        time.sleep(interval)


if __name__ == "__main__":
    main()
