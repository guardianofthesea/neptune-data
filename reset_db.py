import recreate_tables
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Resetting database tables...")
    recreate_tables.recreate_tables()
    logger.info("Database tables have been reset!") 