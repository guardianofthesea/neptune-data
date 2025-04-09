import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import (
    MarketData, TokenRates, TokenAmounts, TokenPrices,
    ContractData, NTokenContractExecutes, MarketContractExecutes,
    NEPTData, StakingPools
)
from database import get_db
import os
from dotenv import load_dotenv
from neptune_data_collector import NeptuneDataCollector

# Load environment variables
load_dotenv()

async def collect_and_store_data():
    # Initialize data collector
    collector = NeptuneDataCollector()
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Collect all data
        market_data = await collector.get_market_data()
        price_data = await collector.get_price_data()
        contract_data = await collector.get_contract_data()
        nept_data = await collector.get_nept_data()
        
        # Get current timestamp
        current_time = datetime.utcnow()
        
        # Store Market Data
        market_record = MarketData(
            timestamp=current_time,
            borrow_accounts_count=market_data['borrow_accounts_count'],
            unique_borrow_addresses=market_data['unique_borrow_addresses']
        )
        db.add(market_record)
        
        # Store Token Rates
        for token, rate in market_data['borrow_rates'].items():
            token_rate = TokenRates(
                timestamp=current_time,
                token_symbol=token,
                borrow_rate=float(rate.strip('%')),
                lend_rate=float(market_data['lending_rates'][token].strip('%'))
            )
            db.add(token_rate)
        
        # Store Token Amounts
        for token, amount in market_data['borrowed_amount'].items():
            token_amount = TokenAmounts(
                timestamp=current_time,
                token_symbol=token,
                borrowed_amount=float(amount),
                lent_amount=float(market_data['lent_amount'][token])
            )
            db.add(token_amount)
        
        # Store Token Prices
        for token, price in price_data['token_prices'].items():
            token_price = TokenPrices(
                timestamp=current_time,
                token_symbol=token,
                price=float(price.strip('$'))
            )
            db.add(token_price)
        
        # Store Contract Data
        contract_record = ContractData(timestamp=current_time)
        db.add(contract_record)
        
        # Store NToken Contract Executes
        for token, count in contract_data['ntoken_contract_executes'].items():
            ntoken_execute = NTokenContractExecutes(
                timestamp=current_time,
                token_symbol=token,
                execute_count=int(count)
            )
            db.add(ntoken_execute)
        
        # Store Market Contract Executes
        for contract_type, count in contract_data['market_contract_executes'].items():
            market_execute = MarketContractExecutes(
                timestamp=current_time,
                contract_type=contract_type,
                execute_count=int(count)
            )
            db.add(market_execute)
        
        # Store NEPT Data
        nept_record = NEPTData(
            timestamp=current_time,
            circulating_supply=float(nept_data['circulating_supply']),
            emission_rate=float(nept_data['emission_rate']),
            total_bonded=float(nept_data['total_bonded'])
        )
        db.add(nept_record)
        
        # Store Staking Pools
        for pool_num, amount in nept_data['staking_amounts'].items():
            pool_num = int(pool_num.split('_')[-1])  # Convert "staking_pool_1" to 1
            staking_pool = StakingPools(
                timestamp=current_time,
                pool_number=pool_num,
                staking_amount=float(amount),
                staking_rate=float(nept_data['staking_rates'][f'pool_{pool_num}'].strip('%'))
            )
            db.add(staking_pool)
        
        # Commit all changes
        db.commit()
        print(f"Data collected and stored successfully at {current_time}")
        
    except Exception as e:
        db.rollback()
        print(f"Error collecting and storing data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(collect_and_store_data()) 