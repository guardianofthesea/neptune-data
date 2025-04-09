from database import Base, engine
from models import (
    MarketData, TokenRates, TokenAmounts, TokenPrices,
    ContractData, NTokenContractExecutes, MarketContractExecutes,
    NEPTData, StakingPools
)

def recreate_tables():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating tables in order...")
    
    # Create parent tables first
    print("Creating MarketData table...")
    MarketData.__table__.create(bind=engine)
    
    print("Creating TokenPrices table...")
    TokenPrices.__table__.create(bind=engine)
    
    print("Creating ContractData table...")
    ContractData.__table__.create(bind=engine)
    
    print("Creating NEPTData table...")
    NEPTData.__table__.create(bind=engine)
    
    # Create child tables
    print("Creating TokenRates table...")
    TokenRates.__table__.create(bind=engine)
    
    print("Creating TokenAmounts table...")
    TokenAmounts.__table__.create(bind=engine)
    
    print("Creating NTokenContractExecutes table...")
    NTokenContractExecutes.__table__.create(bind=engine)
    
    print("Creating MarketContractExecutes table...")
    MarketContractExecutes.__table__.create(bind=engine)
    
    print("Creating StakingPools table...")
    StakingPools.__table__.create(bind=engine)
    
    print("Done!")

if __name__ == "__main__":
    recreate_tables() 