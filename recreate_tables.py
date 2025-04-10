from database import Base, engine
from models import (
    MarketData, TokenRates, TokenAmounts, TokenPrices,
    ContractData, NTokenContractExecutes, MarketContractExecutes,
    NEPTData, StakingPools
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def recreate_tables():
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Creating tables in order...")
    
    # Create parent tables first
    logger.info("Creating MarketData table...")
    MarketData.__table__.create(bind=engine)
    
    logger.info("Creating TokenPrices table...")
    TokenPrices.__table__.create(bind=engine)
    
    logger.info("Creating ContractData table...")
    ContractData.__table__.create(bind=engine)
    
    logger.info("Creating NEPTData table...")
    NEPTData.__table__.create(bind=engine)
    
    # Create child tables
    logger.info("Creating TokenRates table...")
    TokenRates.__table__.create(bind=engine)
    
    logger.info("Creating TokenAmounts table...")
    TokenAmounts.__table__.create(bind=engine)
    
    logger.info("Creating NTokenContractExecutes table...")
    NTokenContractExecutes.__table__.create(bind=engine)
    
    logger.info("Creating MarketContractExecutes table...")
    MarketContractExecutes.__table__.create(bind=engine)
    
    logger.info("Creating StakingPools table...")
    StakingPools.__table__.create(bind=engine)
    
    logger.info("Done!")

if __name__ == "__main__":
    recreate_tables() 