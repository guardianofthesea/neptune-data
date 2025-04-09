import asyncio
import logging
from datetime import datetime
from flask import Flask, jsonify
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates

app = Flask(__name__)

# Global variables to store the latest data
latest_data = {
    'market_data': {},
    'price_data': {},
    'contract_data': {},
    'nept_data': {}
}

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
    
    logger.info("Starting new data fetch cycle")
    logger.info("Fetching market data...")
    
    try:
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
        
        latest_data['market_data'] = {
            'borrow_accounts': borrow_accounts_data,
            'lent_amount': lent_amount,
            'borrowed_amount': borrowed_amount,
            'borrow_rates': borrow_rates,
            'lending_rates': lending_rates,
            'nToken_circulating_supply': nToken_circulating_supply
        }

        logger.info("Fetching price data...")
        token_prices = await get_token_prices(client)
        latest_data['price_data'] = {'token_prices': token_prices}
        logger.info("Successfully fetched token prices")

        logger.info("Fetching contract data...")
        nToken_contract_executes = await get_nToken_contract_executes(client)
        executes = await get_market_contract_executes(client)
        latest_data['contract_data'] = {
            'nToken_contract_executes': nToken_contract_executes,
            'market_contract_executes': executes
        }
        logger.info("Successfully fetched contract data")

        logger.info("Fetching NEPT data...")
        NEPT_circulating_supply = await get_NEPT_circulating_supply()
        NEPT_emission_rate = await get_NEPT_emission_rate(client)
        NEPT_staking_amounts, NEPT_total_bonded = await get_NEPT_staking_amounts(client)
        NEPT_staking_rates = await get_NEPT_staking_rates(client)
        
        latest_data['nept_data'] = {
            'circulating_supply': NEPT_circulating_supply,
            'emission_rate': NEPT_emission_rate,
            'staking_amounts': NEPT_staking_amounts,
            'total_bonded': NEPT_total_bonded,
            'staking_rates': NEPT_staking_rates
        }
        logger.info("Successfully fetched NEPT data")
        
        logger.info("Data fetch cycle completed successfully")
        
    except Exception as e:
        logger.error(f"Error during data fetch: {str(e)}", exc_info=True)
        raise

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
    logger.info("Received request for latest data")
    return jsonify(latest_data)

@app.route('/health')
def health():
    logger.info("Health check requested")
    return jsonify({
        'status': 'healthy',
        'last_update': datetime.now().isoformat(),
        'data_available': bool(latest_data['market_data'])
    })

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
