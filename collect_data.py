import asyncio
import logging
from datetime import datetime
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates
from models import MarketData, TokenPrices, ContractData, NEPTData, TokenRates, TokenAmounts, NTokenContractExecutes, MarketContractExecutes, StakingPools
from database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def collect_and_store_data():
    """Collect and store all data types."""
    try:
        # Initialize Injective client
        client = AsyncClient(Network.mainnet())
        
        # Get database session
        db = next(get_db())
        
        try:
            # Collect and store market data
            logger.info("Fetching market data...")
            market_data = await get_market_contract_executes(client)
            market_data_record = MarketData(market_data=market_data)
            db.add(market_data_record)
            logger.info(f"Successfully fetched and stored market data: {market_data}")

            # Collect and store price data
            logger.info("Fetching price data...")
            token_prices = await get_token_prices(client)
            price_data = TokenPrices(token_prices=token_prices)
            db.add(price_data)
            logger.info(f"Successfully fetched and stored token prices: {token_prices}")

            # Collect and store contract data
            logger.info("Fetching contract data...")
            contract_data = await get_all_borrow_accounts(client)
            contract_data_record = ContractData(contract_data=contract_data)
            db.add(contract_data_record)
            logger.info(f"Successfully fetched and stored contract data: {contract_data}")

            # Collect and store NEPT data
            logger.info("Fetching NEPT data...")
            nept_data = await get_NEPT_emission_rate(client)
            nept_data_record = NEPTData(nept_data=nept_data)
            db.add(nept_data_record)
            logger.info(f"Successfully fetched and stored NEPT data: {nept_data}")

            # Collect and store token rates
            logger.info("Fetching token rates...")
            borrow_rates = await get_borrow_rates(client)
            lending_rates = await get_lending_rates(client)
            staking_rates = await get_NEPT_staking_rates(client)
            token_rates = {
                'borrow_rates': borrow_rates,
                'lending_rates': lending_rates,
                'staking_rates': staking_rates
            }
            token_rates_record = TokenRates(token_rates=token_rates)
            db.add(token_rates_record)
            logger.info(f"Successfully fetched and stored token rates: {token_rates}")

            # Collect and store token amounts
            logger.info("Fetching token amounts...")
            nept_circulating = await get_NEPT_circulating_supply(client)
            ntoken_circulating = await get_nToken_circulating_supply(client)
            lent_amount = await get_lent_amount(client)
            borrowed_amount = await get_borrowed_amount(client)
            token_amounts = {
                'nept_circulating': nept_circulating,
                'ntoken_circulating': ntoken_circulating,
                'lent_amount': lent_amount,
                'borrowed_amount': borrowed_amount
            }
            token_amounts_record = TokenAmounts(token_amounts=token_amounts)
            db.add(token_amounts_record)
            logger.info(f"Successfully fetched and stored token amounts: {token_amounts}")

            # Collect and store nToken contract executes
            logger.info("Fetching nToken contract executes...")
            ntoken_executes = await get_nToken_contract_executes(client)
            ntoken_executes_record = NTokenContractExecutes(ntoken_executes=ntoken_executes)
            db.add(ntoken_executes_record)
            logger.info(f"Successfully fetched and stored nToken contract executes: {ntoken_executes}")

            # Collect and store market contract executes
            logger.info("Fetching market contract executes...")
            market_executes = await get_market_contract_executes(client)
            market_executes_record = MarketContractExecutes(market_executes=market_executes)
            db.add(market_executes_record)
            logger.info(f"Successfully fetched and stored market contract executes: {market_executes}")

            # Commit all changes
            db.commit()
            logger.info("All data successfully collected and stored")

        except Exception as e:
            db.rollback()
            logger.error(f"Error collecting data: {str(e)}")
            raise

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in collect_and_store_data: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(collect_and_store_data()) 