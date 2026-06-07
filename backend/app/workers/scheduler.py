import time

from app.core.scheduler import create_scheduler


def scheduled_market_scan() -> None:
    print("scheduled market scan tick", flush=True)


def main() -> None:
    scheduler = create_scheduler()
    scheduler.add_job(scheduled_market_scan, "interval", minutes=5, id="market-scan")
    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
