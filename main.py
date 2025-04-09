import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates
from models import MarketData, PriceData, ContractData, NEPTData, SessionLocal
from sqlalchemy import desc

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('neptune-data')

async def fetch_data():
    network: Network = Network.mainnet()
    client: AsyncClient = AsyncClient(network)
    db = SessionLocal()
    
    logger.info("Starting new data fetch cycle")
    logger.info("Fetching market data...")
    
    try:
        # Fetch market data
        borrow_accounts_data = await get_all_borrow_accounts(client)
        logger.info(f"Successfully fetched borrow accounts data")
        
        lent_amount = await get_lent_amount(client)
        borrowed_amount = await get_borrowed_amount(client)
        logger.info(f"Successfully fetched lending/borrowing amounts")
        
        borrow_rates = await get_borrow_rates(client)
        lending_rates = await get_lending_rates(client)
        logger.info(f"Successfully fetched interest rates")
        
        nToken_circulating_supply = await get_nToken_circulating_supply()
        logger.info(f"Successfully fetched nToken supply")
        
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

        # Fetch and store price data
        logger.info("Fetching price data...")
        token_prices = await get_token_prices(client)
        price_data = PriceData(token_prices=token_prices)
        db.add(price_data)
        logger.info("Successfully fetched and stored token prices")

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
        logger.info("Successfully fetched and stored NEPT data")
        
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
        
        return jsonify([item.__dict__ for item in data])
    finally:
        db.close()

@app.route('/health')
def health():
    logger.info("Health check requested")
    db = SessionLocal()
    try:
        latest_market_data = db.query(MarketData).order_by(desc(MarketData.timestamp)).first()
        return jsonify({
            'status': 'healthy',
            'last_update': latest_market_data.timestamp.isoformat() if latest_market_data else None,
            'data_available': bool(latest_market_data)
        })
    finally:
        db.close()

def start_background_tasks():
    logger.info("Starting background tasks")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_periodically())

if __name__ == "__main__":
    # Start background tasks
    start_background_tasks()
    
    # Run Flask app
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8080)
