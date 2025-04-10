from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/neptune_data')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class MarketData(Base):
    __tablename__ = "market_data"
    
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow, unique=True)
    borrow_accounts_count = Column(Integer)
    unique_borrow_addresses = Column(Integer)
    
    # Relationships
    token_rates = relationship("TokenRates", back_populates="market_data")
    token_amounts = relationship("TokenAmounts", back_populates="market_data")

class TokenRates(Base):
    __tablename__ = "token_rates"
    
    timestamp = Column(DateTime, ForeignKey('market_data.timestamp'), primary_key=True)
    token_symbol = Column(String(10), primary_key=True)
    borrow_rate = Column(DECIMAL(10,4))
    lend_rate = Column(DECIMAL(10,4))
    
    # Relationship
    market_data = relationship("MarketData", back_populates="token_rates")

class TokenAmounts(Base):
    __tablename__ = "token_amounts"
    
    timestamp = Column(DateTime, ForeignKey('market_data.timestamp'), primary_key=True)
    token_symbol = Column(String(10), primary_key=True)
    borrowed_amount = Column(DECIMAL(20,8))
    lent_amount = Column(DECIMAL(20,8))
    
    # Relationship
    market_data = relationship("MarketData", back_populates="token_amounts")

class TokenPrices(Base):
    __tablename__ = "token_prices"
    
    timestamp = Column(DateTime, primary_key=True, unique=True)
    token_symbol = Column(String(10), primary_key=True)
    price = Column(DECIMAL(20,8))

class ContractData(Base):
    __tablename__ = "contract_data"
    
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow, unique=True)
    
    # Relationships
    ntoken_executes = relationship("NTokenContractExecutes", back_populates="contract_data")
    market_executes = relationship("MarketContractExecutes", back_populates="contract_data")

class NTokenContractExecutes(Base):
    __tablename__ = "ntoken_contract_executes"
    
    timestamp = Column(DateTime, ForeignKey('contract_data.timestamp'), primary_key=True)
    token_symbol = Column(String(10), primary_key=True)
    execute_count = Column(Integer)
    
    # Relationship
    contract_data = relationship("ContractData", back_populates="ntoken_executes")

class MarketContractExecutes(Base):
    __tablename__ = "market_contract_executes"
    
    timestamp = Column(DateTime, ForeignKey('contract_data.timestamp'), primary_key=True)
    contract_type = Column(String(50), primary_key=True)
    execute_count = Column(Integer)
    
    # Relationship
    contract_data = relationship("ContractData", back_populates="market_executes")

class NEPTData(Base):
    __tablename__ = "nept_data"
    
    timestamp = Column(DateTime, primary_key=True, default=datetime.utcnow, unique=True)
    circulating_supply = Column(DECIMAL(20,8))
    emission_rate = Column(DECIMAL(10,4))
    total_bonded = Column(DECIMAL(20,8))
    
    # Relationship
    staking_pools = relationship("StakingPools", back_populates="nept_data")

class StakingPools(Base):
    __tablename__ = "staking_pools"
    
    timestamp = Column(DateTime, ForeignKey('nept_data.timestamp'), primary_key=True)
    pool_number = Column(Integer, primary_key=True)
    staking_amount = Column(DECIMAL(20,8))
    staking_rate = Column(DECIMAL(10,4))
    
    # Relationship
    nept_data = relationship("NEPTData", back_populates="staking_pools") 