#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path


def main() -> None:
    log_path = Path(__file__).with_name("cron_log.txt")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"cron ran at {datetime.now()}\n")


if __name__ == "__main__":
    main()