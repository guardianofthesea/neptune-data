import asyncio
import logging
from datetime import datetime


from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates

async def main() -> None:
    app.run(host='0.0.0.0', port=8080)

    network: Network = Network.mainnet()
    client: AsyncClient = AsyncClient(network)
    
    logging.info("============NEW RUN============")
    logging.info("=MARKET DATA=")
    
    borrow_accounts_data = await get_all_borrow_accounts(client)
    logging.info(f"Total number of borrow accounts: {borrow_accounts_data['total_accounts_count']}")
    logging.info(f"Number of unique borrow addresses: {borrow_accounts_data['unique_addresses_count']}")

    lent_amount = await get_lent_amount(client)
    logging.info(f"Lent amount: {lent_amount}")

    borrowed_amount = await get_borrowed_amount(client)
    logging.info(f"Borrowed amount: {borrowed_amount}")

    borrow_rates = await get_borrow_rates(client)
    logging.info(f"Borrow rates: {borrow_rates}")

    lending_rates = await get_lending_rates(client)
    logging.info(f"Lending rates: {lending_rates}")

    nToken_circulating_supply = await get_nToken_circulating_supply()
    logging.info(f"nToken circulating supply: {nToken_circulating_supply}")

    logging.info("=PRICE DATA=")

    token_prices = await get_token_prices(client)
    logging.info(f"Token prices: {token_prices}")

    logging.info("=CONTRACT DATA=")
    
    nToken_contract_executes = await get_nToken_contract_executes(client)
    logging.info(f"nToken contract executes: {nToken_contract_executes}")

    executes = await get_market_contract_executes(client)
    logging.info(f"Market contract executes: {executes}")

    logging.info("=NEPT DATA=")

    NEPT_circulating_supply = await get_NEPT_circulating_supply()
    logging.info(f"NEPT circulating supply: {NEPT_circulating_supply}")

    NEPT_emission_rate = await get_NEPT_emission_rate(client)
    logging.info(f"NEPT emission rate: {NEPT_emission_rate} (annual)")

    NEPT_staking_amounts, NEPT_total_bonded = await get_NEPT_staking_amounts(client)
    logging.info(f"NEPT staking amounts: {NEPT_staking_amounts}")
    logging.info(f"NEPT total bonded: {NEPT_total_bonded}")

    NEPT_staking_rates = await get_NEPT_staking_rates(client)
    logging.info(f"NEPT staking rates: {NEPT_staking_rates}")


    
    

async def run_periodically():
    while True:
        try:
            await main()
        except Exception as e:
            logging.error(f"Error in main execution: {str(e)}")
        
        # Wait for 24 hours before next execution
        await asyncio.sleep(24 * 60 * 60)  # 24 hours in seconds

if __name__ == "__main__":
    # Configure logging to save to a file and output to console
    log_format = '%(asctime)s - %(message)s'
    
    # Create logger and remove any existing handlers
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create file handler
    file_handler = logging.FileHandler('Neptune_data.log')
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Run the periodic task
    asyncio.run(run_periodically())
