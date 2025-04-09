from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    borrow_accounts_count = Column(Integer)
    unique_borrow_addresses = Column(Integer)
    lent_amount = Column(Float)
    borrowed_amount = Column(Float)
    borrow_rates = Column(JSON)
    lending_rates = Column(JSON)
    ntoken_circulating_supply = Column(Float)

class PriceData(Base):
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    token_prices = Column(JSON)

class ContractData(Base):
    __tablename__ = "contract_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ntoken_contract_executes = Column(JSON)
    market_contract_executes = Column(JSON)

class NEPTData(Base):
    __tablename__ = "nept_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    circulating_supply = Column(Float)
    emission_rate = Column(Float)
    staking_amounts = Column(JSON)
    total_bonded = Column(Float)
    staking_rates = Column(JSON)

# Create all tables
Base.metadata.create_all(bind=engine) 