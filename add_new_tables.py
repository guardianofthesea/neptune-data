from database import Base, engine
from models import LPPoolData
import logging

# Get the logger
logger = logging.getLogger('neptune-data')

def add_new_tables():
    logger.info("Creating new tables...")
    
    # This will only create tables that don't already exist
    Base.metadata.create_all(bind=engine)
    
    logger.info("Done! New tables have been created without affecting existing data.")

if __name__ == "__main__":
    add_new_tables() 