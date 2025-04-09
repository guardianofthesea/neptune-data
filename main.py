import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates
from models import MarketData, PriceData, ContractData, NEPTData, SessionLocal
from sqlalchemy import desc
import threading
import os
import time
from collect_data import collect_and_store_data
import schedule

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
    global background_thread
    try:
        logger.info("Starting background tasks thread")
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
        # Fetch market data
        borrow_accounts_data = await get_all_borrow_accounts(client)
        logger.info(f"Successfully fetched borrow accounts data: {borrow_accounts_data}")
        
        lent_amount = await get_lent_amount(client)
        borrowed_amount = await get_borrowed_amount(client)
        logger.info(f"Successfully fetched lending/borrowing amounts: {lent_amount}, {borrowed_amount}")
        
        borrow_rates = await get_borrow_rates(client)
        lending_rates = await get_lending_rates(client)
        logger.info(f"Successfully fetched interest rates")
        
        nToken_circulating_supply = await get_nToken_circulating_supply()
        logger.info(f"Successfully fetched nToken supply: {nToken_circulating_supply}")
        
        # Store market data
        market_data = MarketData(
            borrow_accounts_count=borrow_accounts_data['total_accounts_count'],
            unique_borrow_addresses=borrow_accounts_data['unique_addresses_count'],
            lent_amount=lent_amount,
            borrowed_amount=borrowed_amount,
            borrow_rates=borrow_rates,
            lending_rates=lending_rates,
            ntoken_circulating_supply=nToken_circulating_supply
        )
        db.add(market_data)
        logger.info("Added market data to database")

        # Fetch and store price data
        logger.info("Fetching price data...")
        token_prices = await get_token_prices(client)
        price_data = PriceData(token_prices=token_prices)
        db.add(price_data)
        logger.info(f"Successfully fetched and stored token prices: {token_prices}")

        # Fetch and store contract data
        logger.info("Fetching contract data...")
        nToken_contract_executes = await get_nToken_contract_executes(client)
        executes = await get_market_contract_executes(client)
        contract_data = ContractData(
            ntoken_contract_executes=nToken_contract_executes,
            market_contract_executes=executes
        )
        db.add(contract_data)
        logger.info("Successfully fetched and stored contract data")

        # Fetch and store NEPT data
        logger.info("Fetching NEPT data...")
        NEPT_circulating_supply = await get_NEPT_circulating_supply()
        NEPT_emission_rate = await get_NEPT_emission_rate(client)
        NEPT_staking_amounts, NEPT_total_bonded = await get_NEPT_staking_amounts(client)
        NEPT_staking_rates = await get_NEPT_staking_rates(client)
        
        nept_data = NEPTData(
            circulating_supply=NEPT_circulating_supply,
            emission_rate=NEPT_emission_rate,
            staking_amounts=NEPT_staking_amounts,
            total_bonded=NEPT_total_bonded,
            staking_rates=NEPT_staking_rates
        )
        db.add(nept_data)
        logger.info(f"Successfully fetched and stored NEPT data: supply={NEPT_circulating_supply}, bonded={NEPT_total_bonded}")
        
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
        await asyncio.sleep(60)  # 24 hours in seconds

@app.route('/')
def index():
    """Get the latest data from all categories"""
    logger.info("Received request for latest data")
    db = SessionLocal()
    try:
        latest_data = {
            'market_data': db.query(MarketData).order_by(desc(MarketData.timestamp)).first(),
            'price_data': db.query(PriceData).order_by(desc(PriceData.timestamp)).first(),
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
            'price': PriceData,
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
            'background_task_running': bool(background_task and not background_task.done())
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

def start_background_tasks():
    # Run immediately on startup
    job()
    
    # Schedule to run every 5 minutes
    schedule.every(5).minutes.do(job)

@app.route('/')
def home():
    return "Neptune Data Collector is running"

# Start background tasks when the application starts
start_background_tasks()

if __name__ == "__main__":
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080)
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(1)
