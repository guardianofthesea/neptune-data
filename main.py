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

async def fetch_data():
    network: Network = Network.mainnet()
    client: AsyncClient = AsyncClient(network)
    
    logging.info("============NEW RUN============")
    logging.info("=MARKET DATA=")
    
    borrow_accounts_data = await get_all_borrow_accounts(client)
    lent_amount = await get_lent_amount(client)
    borrowed_amount = await get_borrowed_amount(client)
    borrow_rates = await get_borrow_rates(client)
    lending_rates = await get_lending_rates(client)
    nToken_circulating_supply = await get_nToken_circulating_supply()
    
    latest_data['market_data'] = {
        'borrow_accounts': borrow_accounts_data,
        'lent_amount': lent_amount,
        'borrowed_amount': borrowed_amount,
        'borrow_rates': borrow_rates,
        'lending_rates': lending_rates,
        'nToken_circulating_supply': nToken_circulating_supply
    }

    logging.info("=PRICE DATA=")
    token_prices = await get_token_prices(client)
    latest_data['price_data'] = {'token_prices': token_prices}

    logging.info("=CONTRACT DATA=")
    nToken_contract_executes = await get_nToken_contract_executes(client)
    executes = await get_market_contract_executes(client)
    latest_data['contract_data'] = {
        'nToken_contract_executes': nToken_contract_executes,
        'market_contract_executes': executes
    }

    logging.info("=NEPT DATA=")
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

async def run_periodically():
    while True:
        try:
            await fetch_data()
        except Exception as e:
            logging.error(f"Error in data fetch: {str(e)}")
        
        await asyncio.sleep(24 * 60 * 60)  # 24 hours in seconds

@app.route('/')
def index():
    return jsonify(latest_data)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

def start_background_tasks():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_periodically())

if __name__ == "__main__":
    # Configure logging
    log_format = '%(asctime)s - %(message)s'
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    file_handler = logging.FileHandler('Neptune_data.log')
    file_handler.setFormatter(logging.Formatter(log_format))
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Start background tasks
    start_background_tasks()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=8080)
