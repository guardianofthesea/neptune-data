import recreate_tables
import logging

# Get the logger
logger = logging.getLogger('neptune-data')

if __name__ == "__main__":
    logger.info("Resetting database tables...")
    recreate_tables.recreate_tables()
    logger.info("Database tables have been reset!") 