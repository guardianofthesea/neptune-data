import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import (
    get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, 
    get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, 
    get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, 
    get_nToken_contract_executes, get_NEPT_staking_rates
)
from models import (
    MarketData, TokenPrices, ContractData, NEPTData, SessionLocal, 
    TokenAmounts, TokenRates, NTokenContractExecutes, MarketContractExecutes, StakingPools
)
from sqlalchemy import desc
import threading
import os
import time
from collect_data import collect_and_store_data
import schedule
from database import get_db

app = Flask(__name__)

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('neptune-data')

# Global event loop for background tasks
background_loop = None
background_thread = None
background_task = None
collection_thread = None

def run_background_loop():
    global background_loop, background_task
    try:
        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(background_loop)
        background_task = background_loop.create_task(run_periodically())
        background_loop.run_forever()
    except Exception as e:
        logger.error(f"Error in background loop: {str(e)}", exc_info=True)
        raise

def start_background_tasks():
    global background_thread, collection_thread
    try:
        # Start data collection thread
        logger.info("Starting background tasks thread for data collection")
        # Run immediately on startup
        job()
        
        # Schedule to run every 5 minutes
        schedule.every(5).minutes.do(job)
        
        # Start scheduler in a separate thread
        collection_thread = threading.Thread(target=run_scheduler)
        collection_thread.daemon = True
        collection_thread.start()
        
        # Start data fetching background thread
        logger.info("Starting background tasks thread for API data fetch")
        background_thread = threading.Thread(target=run_background_loop)
        background_thread.daemon = True
        background_thread.start()
        
        # Wait a moment to ensure the loop is running
        time.sleep(1)
        
        if background_loop is None or not background_loop.is_running():
            raise RuntimeError("Background loop failed to start")
            
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Failed to start background tasks: {str(e)}", exc_info=True)
        raise

async def fetch_data():
    network: Network = Network.mainnet()
    client: AsyncClient = AsyncClient(network)
    db = SessionLocal()
    
    logger.info("Starting new data fetch cycle")
    logger.info("Fetching market data...")
    
    try:
        # Create timestamp for consistency across records
        current_timestamp = datetime.utcnow()
        
        # Fetch market data
        borrow_accounts_data = await get_all_borrow_accounts(client)
        logger.info(f"Successfully fetched borrow accounts data: {borrow_accounts_data}")
        
        # Store market data
        market_data = MarketData(
            timestamp=current_timestamp,
            borrow_accounts_count=borrow_accounts_data['total_accounts_count'],
            unique_borrow_addresses=borrow_accounts_data['unique_addresses_count']
        )
        db.add(market_data)
        logger.info("Added market data to database")

        # Fetch and store token amounts
        logger.info("Fetching lending/borrowing amounts...")
        lent_amounts = await get_lent_amount(client)
        borrowed_amounts = await get_borrowed_amount(client)
        logger.info(f"Successfully fetched lending/borrowing amounts")
        
        for token_symbol in set(list(lent_amounts.keys()) + list(borrowed_amounts.keys())):
            lent_amount_value = lent_amounts.get(token_symbol, 0)
            borrowed_amount_value = borrowed_amounts.get(token_symbol, 0)
            
            token_amount = TokenAmounts(
                timestamp=current_timestamp,
                token_symbol=token_symbol,
                lent_amount=lent_amount_value,
                borrowed_amount=borrowed_amount_value
            )
            db.add(token_amount)
        
        # Fetch and store token rates 
        logger.info("Fetching interest rates...")
        borrow_rates_data = await get_borrow_rates(client)
        lending_rates_data = await get_lending_rates(client)
        logger.info(f"Successfully fetched interest rates")
        
        for token_symbol, borrow_rate in borrow_rates_data.items():
            lend_rate = lending_rates_data.get(token_symbol, "0%")
            
            # Remove % symbol and convert to float
            borrow_rate_value = float(borrow_rate.replace('%', ''))
            lend_rate_value = float(lend_rate.replace('%', ''))
            
            token_rate = TokenRates(
                timestamp=current_timestamp,
                token_symbol=token_symbol,
                borrow_rate=borrow_rate_value,
                lend_rate=lend_rate_value
            )
            db.add(token_rate)

        # Fetch and store price data
        logger.info("Fetching price data...")
        token_prices_data = await get_token_prices(client)
        
        for token_symbol, price in token_prices_data.items():
            # Remove $ symbol
            price_value = price.replace('$', '')
            price_data = TokenPrices(
                timestamp=current_timestamp,
                token_symbol=token_symbol,
                price=price_value
            )
            db.add(price_data)
        logger.info(f"Successfully fetched and stored token prices")

        # Fetch and store contract data
        logger.info("Fetching contract data...")
        contract_data_record = ContractData(
            timestamp=current_timestamp
        )
        db.add(contract_data_record)
        logger.info("Successfully created contract data record")
        
        # Fetch and store nToken contract executes
        ntoken_executes_data = await get_nToken_contract_executes(client)
        for token_symbol, execute_count in ntoken_executes_data.items():
            if execute_count is not None:
                ntoken_record = NTokenContractExecutes(
                    timestamp=current_timestamp,
                    token_symbol=token_symbol,
                    execute_count=execute_count
                )
                db.add(ntoken_record)
        
        # Fetch and store market contract executes
        market_executes = await get_market_contract_executes(client)
        if market_executes:
            market_executes_record = MarketContractExecutes(
                timestamp=current_timestamp,
                contract_type="market",
                execute_count=market_executes
            )
            db.add(market_executes_record)
        logger.info("Successfully fetched and stored contract data")

        # Fetch and store NEPT data
        logger.info("Fetching NEPT data...")
        try:
            NEPT_circulating_supply = await get_NEPT_circulating_supply()
            NEPT_emission_rate = await get_NEPT_emission_rate(client)
            NEPT_staking_amounts, NEPT_total_bonded = await get_NEPT_staking_amounts(client)
            
            nept_data = NEPTData(
                timestamp=current_timestamp,
                circulating_supply=NEPT_circulating_supply,
                emission_rate=NEPT_emission_rate,
                total_bonded=NEPT_total_bonded
            )
            db.add(nept_data)
            
            # Store staking pools data
            staking_rates = await get_NEPT_staking_rates(client)
            for pool_number, staking_amount in NEPT_staking_amounts.items():
                # Extract just the numeric part from 'staking_pool_1'
                pool_num = ''.join(filter(str.isdigit, pool_number))
                pool_key = f"pool_{pool_num}"
                staking_rate = staking_rates.get(pool_key, "0%").replace('%', '')
                
                pool_record = StakingPools(
                    timestamp=current_timestamp,
                    pool_number=int(pool_num),
                    staking_amount=staking_amount,
                    staking_rate=float(staking_rate)
                )
                db.add(pool_record)
                
            logger.info(f"Successfully fetched and stored NEPT data: supply={NEPT_circulating_supply}, bonded={NEPT_total_bonded}")
        except Exception as e:
            logger.error(f"Error processing NEPT data: {str(e)}")
        
        # Commit all changes
        db.commit()
        logger.info("Data fetch cycle completed successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during data fetch: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()

async def run_periodically():
    logger.info("Starting periodic data fetch")
    while True:
        try:
            await fetch_data()
        except Exception as e:
            logger.error(f"Error in periodic data fetch: {str(e)}", exc_info=True)
        
        logger.info("Waiting 24 hours until next data fetch")
        await asyncio.sleep(86400)  # 24 hours in seconds = 86400

@app.route('/')
def index():
    """Get the latest data from all categories"""
    logger.info("Received request for latest data")
    db = SessionLocal()
    try:
        latest_data = {
            'market_data': db.query(MarketData).order_by(desc(MarketData.timestamp)).first(),
            'price_data': db.query(TokenPrices).order_by(desc(TokenPrices.timestamp)).first(),
            'contract_data': db.query(ContractData).order_by(desc(ContractData.timestamp)).first(),
            'nept_data': db.query(NEPTData).order_by(desc(NEPTData.timestamp)).first()
        }
        logger.info(f"Returning latest data: {latest_data}")
        return jsonify({
            k: v.__dict__ if v else None 
            for k, v in latest_data.items()
        })
    finally:
        db.close()

@app.route('/historical/<data_type>/<int:days>')
def historical_data(data_type, days):
    """Get historical data for a specific type over a number of days"""
    logger.info(f"Received request for historical {data_type} data for {days} days")
    db = SessionLocal()
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        model_map = {
            'market': MarketData,
            'price': TokenPrices,
            'contract': ContractData,
            'nept': NEPTData
        }
        
        if data_type not in model_map:
            return jsonify({'error': 'Invalid data type'}), 400
            
        model = model_map[data_type]
        data = db.query(model).filter(
            model.timestamp >= start_date,
            model.timestamp <= end_date
        ).order_by(model.timestamp).all()
        
        logger.info(f"Returning {len(data)} historical records")
        return jsonify([item.__dict__ for item in data])
    finally:
        db.close()

@app.route('/health')
def health():
    logger.info("Health check requested")
    db = SessionLocal()
    try:
        latest_market_data = db.query(MarketData).order_by(desc(MarketData.timestamp)).first()
        status = {
            'status': 'healthy',
            'last_update': latest_market_data.timestamp.isoformat() if latest_market_data else None,
            'data_available': bool(latest_market_data),
            'background_thread_running': bool(background_thread and background_thread.is_alive()),
            'background_loop_running': bool(background_loop and background_loop.is_running()),
            'background_task_running': bool(background_task and not background_task.done()),
            'collection_thread_running': bool(collection_thread and collection_thread.is_alive())
        }
        logger.info(f"Health check status: {status}")
        return jsonify(status)
    finally:
        db.close()

async def run_collection():
    print(f"Starting data collection at {datetime.utcnow()}")
    await collect_and_store_data()

def job():
    asyncio.run(run_collection())

def run_scheduler():
    """Run the scheduler in a separate thread"""
    logger.info("Starting scheduler thread")
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start background tasks when the application starts
start_background_tasks()

if __name__ == "__main__":
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080)
