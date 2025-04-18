import asyncio
import logging
from datetime import datetime
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from queries import get_market_contract_executes, get_all_borrow_accounts, get_NEPT_emission_rate, get_borrow_rates, get_lending_rates, get_NEPT_staking_amounts, get_NEPT_circulating_supply, get_nToken_circulating_supply, get_lent_amount, get_borrowed_amount, get_token_prices, get_nToken_contract_executes, get_NEPT_staking_rates, get_collateral_amounts, get_LP_info
from models import MarketData, TokenPrices, ContractData, NEPTData, TokenRates, TokenAmounts, NTokenContractExecutes, MarketContractExecutes, StakingPools, CollateralAmounts, LPPoolData
from database import get_db

# Get the logger
logger = logging.getLogger('neptune-data')

async def collect_and_store_data():
    """Collect and store all data types."""
    try:
        # Initialize Injective client
        client = AsyncClient(Network.mainnet())
        
        # Get database session
        db = next(get_db())
        
        try:
            # Create timestamp for consistency across records
            current_timestamp = datetime.utcnow()
            
            # Collect and store market data
            logger.info("Fetching market data...")
            borrow_accounts_data = await get_all_borrow_accounts(client)
            
            market_data_record = MarketData(
                timestamp=current_timestamp,
                borrow_accounts_count=borrow_accounts_data['total_accounts_count'],
                unique_borrow_addresses=borrow_accounts_data['unique_addresses_count']
            )
            db.add(market_data_record)
            logger.info(f"Successfully fetched and stored market data")

            # Collect and store price data
            logger.info("Fetching price data...")
            token_prices_data = await get_token_prices(client)
            
            # For each token price, create a separate record
            for token_symbol, price in token_prices_data.items():
                price_value = price.replace('$', '')  # Remove $ symbol
                try:
                    price_data = TokenPrices(
                        timestamp=current_timestamp,
                        token_symbol=token_symbol,
                        price=price_value
                    )
                    db.add(price_data)
                except Exception as e:
                    logger.warning(f"Error adding token price for {token_symbol}: {str(e)}")
                    # If there's an error, try to get the existing record and update it
                    try:
                        existing_price = db.query(TokenPrices).filter_by(
                            timestamp=current_timestamp, 
                            token_symbol=token_symbol
                        ).first()
                        if existing_price:
                            existing_price.price = price_value
                    except Exception as inner_e:
                        logger.error(f"Error updating token price for {token_symbol}: {str(inner_e)}")
            
            logger.info(f"Successfully fetched and stored token prices")

            # Collect and store contract data
            logger.info("Fetching contract data...")
            contract_data_record = ContractData(
                timestamp=current_timestamp
            )
            db.add(contract_data_record)
            logger.info(f"Successfully added contract data record")

            # Collect and store market executes
            logger.info("Fetching market contract executes...")
            market_executes = await get_market_contract_executes(client)
            if market_executes:
                market_executes_record = MarketContractExecutes(
                    timestamp=current_timestamp,
                    contract_type="market",
                    execute_count=market_executes
                )
                db.add(market_executes_record)
                logger.info(f"Successfully stored market contract executes")

            # Collect and store NEPT data
            logger.info("Fetching NEPT data...")
            emission_rate = await get_NEPT_emission_rate(client)
            staking_amounts, total_bonded = await get_NEPT_staking_amounts(client)
            circulating_supply = await get_NEPT_circulating_supply()
            
            try:
                circulating_supply = float(circulating_supply)
            except ValueError:
                logger.warning(f"Could not convert circulating supply to float: {circulating_supply}")
                circulating_supply = 0
                
            nept_data_record = NEPTData(
                timestamp=current_timestamp,
                circulating_supply=circulating_supply,
                emission_rate=emission_rate,
                total_bonded=total_bonded
            )
            db.add(nept_data_record)
            logger.info(f"Successfully stored NEPT data")
            
            # Store staking pools data
            staking_rates = await get_NEPT_staking_rates(client)  # Get rates once
            for pool_number, staking_amount in staking_amounts.items():
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
            
            # Collect and store token rates
            logger.info("Fetching token rates...")
            borrow_rates_data = await get_borrow_rates(client)
            lending_rates_data = await get_lending_rates(client)
            
            # For each token, create a rate record
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
            
            logger.info(f"Successfully stored token rates")

            # Collect and store token amounts
            logger.info("Fetching token amounts...")
            lent_amounts = await get_lent_amount(client)
            borrowed_amounts = await get_borrowed_amount(client)
            
            # For each token, create an amount record
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
            
            logger.info(f"Successfully stored token amounts")

            # Collect and store nToken contract executes
            logger.info("Fetching nToken contract executes...")
            ntoken_executes_data = await get_nToken_contract_executes(client)
            
            # For each nToken, create an execute record
            for token_symbol, execute_count in ntoken_executes_data.items():
                if execute_count is not None:
                    ntoken_record = NTokenContractExecutes(
                        timestamp=current_timestamp,
                        token_symbol=token_symbol,
                        execute_count=execute_count
                    )
                    db.add(ntoken_record)
            
            logger.info(f"Successfully stored nToken contract executes")

            # Collect and store collateral amounts
            logger.info("Fetching collateral amounts...")
            collateral_amounts_data = await get_collateral_amounts(client)
            
            # For each token, create a collateral amount record
            for token_symbol, amount in collateral_amounts_data.items():
                collateral_record = CollateralAmounts(
                    timestamp=current_timestamp,
                    token_symbol=token_symbol,
                    amount=amount
                )
                db.add(collateral_record)
            
            logger.info(f"Successfully stored collateral amounts")

            # Collect and store LP pool data
            logger.info("Fetching LP pool data...")
            lp_pool_data = await get_LP_info(client)
            
            if lp_pool_data:
                # Use a dictionary to store unique pools by pool_address
                unique_pools = {}
                for pool in lp_pool_data:
                    pool_address = pool["pool_address"]
                    if pool_address not in unique_pools:
                        unique_pools[pool_address] = pool
                    else:
                        logger.warning(f"Duplicate pool address found: {pool_address}. Using first occurrence.")
                
                # Store only unique pools
                for pool in unique_pools.values():
                    lp_pool_record = LPPoolData(
                        timestamp=current_timestamp,
                        pool_address=pool["pool_address"],
                        LP_symbol=pool["LP_symbol"],
                        total_liquidity_usd=pool["total_liquidity_usd"],
                        day_volume_usd=pool["day_volume_usd"],
                        day_LP_fees_usd=pool["day_LP_fees_usd"],
                        yield_pool_fees=pool["yield_pool_fees"],
                        yield_astro_rewards=pool["yield_astro_rewards"],
                        yield_external_rewards=pool["yield_external_rewards"],
                        yield_total=pool["yield_total"]
                    )
                    db.add(lp_pool_record)
                logger.info(f"Successfully stored LP pool data for {len(unique_pools)} unique pools")
            else:
                logger.warning("No LP pool data was fetched")

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