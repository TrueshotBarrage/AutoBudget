#!/usr/bin/env python3
import logging
import sys
from pathlib import Path

from utils.config import Config
from utils.db import DatabaseConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ExportTransactions")

# Target path for the CSV export
EXPORT_PATH = Path(
    "/Users/trueshot/Library/CloudStorage/GoogleDrive-heydavidkim7@gmail.com/My Drive/Financials/transactions.csv"
)


def export_transactions():
    try:
        # Load configuration
        config_path = Path(__file__).parent / "config.json"
        if not config_path.exists():
            logger.error(f"Config file not found at {config_path}")
            return

        cfg = Config(config_path=str(config_path))
        db_details = cfg.get_db_details()

        # Connect to database
        logger.info("Connecting to database...")
        db = DatabaseConnector(**db_details)

        # Ensure export directory exists
        if not EXPORT_PATH.parent.exists():
            logger.info(f"Creating directory: {EXPORT_PATH.parent}")
            EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Perform the export using COPY TO STDOUT
        logger.info(f"Exporting messages to {EXPORT_PATH}...")

        with open(EXPORT_PATH, "w", encoding="utf-8") as f:
            with db.conn.cursor() as cursor:
                copy_sql = "COPY messages TO STDOUT WITH CSV HEADER DELIMITER ','"
                cursor.copy_expert(copy_sql, f)

        logger.info("Export completed successfully.")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if "db" in locals() and hasattr(db, "conn"):
            db.conn.close()


if __name__ == "__main__":
    export_transactions()
