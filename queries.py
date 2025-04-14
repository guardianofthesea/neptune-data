import json
import base64
import time
from pyinjective.client.model.pagination import PaginationOption
from datetime import datetime
import asyncio
import requests
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
import decimal
import aiohttp
import csv
import os
import logging

# Get the logger
logger = logging.getLogger('neptune-data')

# Cache for CSV data to avoid repeated file access
_tokens_cache = None
_staking_pools_cache = None

def _load_tokens():
    """Load tokens from CSV file and cache them"""
    global _tokens_cache
    if _tokens_cache is None:
        _tokens_cache = []
        try:
            with open('tokens.csv') as f:
                tokens = csv.DictReader(f)
                _tokens_cache = list(tokens)
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            _tokens_cache = []
    return _tokens_cache

def _load_staking_pools():
    """Load staking pools from CSV file and cache them"""
    global _staking_pools_cache
    if _staking_pools_cache is None:
        _staking_pools_cache = []
        try:
            with open('staking_pools.csv') as f:
                staking_pools = csv.DictReader(f)
                _staking_pools_cache = list(staking_pools)
        except Exception as e:
            logger.error(f"Error loading staking pools: {e}")
            _staking_pools_cache = []
    return _staking_pools_cache

def _get_token_info(denom):
    """Get token information from the cached token data"""
    tokens = _load_tokens()
    for token in tokens:
        if token['denom'] == denom:
            return token
    return None

async def get_market_contract_executes(client):
    logger.info("Getting market contract executes")

    wasm_contract = await client.fetch_wasm_contract_by_address(address="inj1nc7gjkf2mhp34a6gquhurg8qahnw5kxs5u3s4u")

    if isinstance(wasm_contract, dict) and "executes" in wasm_contract:
        return wasm_contract["executes"]
    else:
        return None


async def get_all_borrow_accounts(client):
    logger.info("Getting all borrow accounts")
    address = "inj1nc7gjkf2mhp34a6gquhurg8qahnw5kxs5u3s4u"
    limit = 100  # Number of accounts to fetch per request
    
    all_accounts = []
    start_after = None
    
    while True:
        # Build query based on whether we have a start_after cursor
        if start_after:
            query_data = json.dumps({
                "get_all_accounts": {
                    "start_after": start_after,
                    "limit": limit
                }
            })
        else:
            query_data = json.dumps({
                "get_all_accounts": {
                    "limit": limit
                }
            })
        
        # Fetch data
        contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
        decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
        accounts_data = json.loads(decoded_data)
        
        # If no accounts returned, we've reached the end
        if not accounts_data:
            break
            
        # Add fetched accounts to our collection
        all_accounts.extend(accounts_data)
        
        # If we got fewer accounts than the limit, we've reached the end
        if len(accounts_data) < limit:
            break
        
        # Set the start_after to the last account for next iteration
        # Format: [account_address, index]
        last_account = accounts_data[-1]
        start_after = [last_account[0][0], last_account[0][1]]
        
        #print(f"Fetched {len(accounts_data)} accounts. Total so far: {len(all_accounts)}")
    
    # Count total accounts and unique addresses
    total_accounts = len(all_accounts)
    unique_addresses = set()
    
    for account_data in all_accounts:
        account_address = account_data[0][0]  # Extract account address
        unique_addresses.add(account_address)
    
    # Return data with both total accounts and unique addresses count
    return {
        "total_accounts_count": total_accounts,
        "unique_addresses_count": len(unique_addresses)
    }


async def get_borrow_rates(client):
    logger.info("Getting rates")
    address = "inj1ftech0pdjrjawltgejlmpx57cyhsz6frdx2dhq"
    query_data = '{"get_all_borrow_rates": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    rates_data = json.loads(decoded_data)
    
    rates_dict = {}
    for rate in rates_data:
        denom = rate[0]["native_token"]["denom"]
        rate_value = round(float(rate[1])*100,2)
        token_info = _get_token_info(denom)
        if token_info:
            ticker = token_info['ticker']
            rates_dict[ticker] = str(rate_value)+"%"
    
    return rates_dict

async def get_lending_rates(client):
    logger.info("Getting rates")
    address = "inj1ftech0pdjrjawltgejlmpx57cyhsz6frdx2dhq"
    query_data = '{"get_all_lending_rates": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    rates_data = json.loads(decoded_data)
    
    rates_dict = {}
    for rate in rates_data:
        denom = rate[0]["native_token"]["denom"]
        rate_value = round(float(rate[1])*100,2)
        token_info = _get_token_info(denom)
        if token_info:
            ticker = token_info['ticker']
            rates_dict[ticker] = str(rate_value)+"%"
    
    return rates_dict

async def get_NEPT_staking_amounts(client):
    logger.info("Getting staking yields")
    address = "inj1v3a4zznudwpukpr8y987pu5gnh4xuf7v36jhva"
    query_data = '{"get_state": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    staking_data = json.loads(decoded_data)

    bonded_dict = {}
    # Access the bonded list directly from staking_data
    staking_pools = _load_staking_pools()
    for bond_entry in staking_data["bonded"]:
        pool_duration = bond_entry[0]
        amount = float(bond_entry[1])/10**6
        for staking_pool in staking_pools:
            if str(pool_duration) == staking_pool['period_nano']:  # Convert pool_duration to string for comparison
                pool = staking_pool['staking_pool']
                bonded_dict[pool] = amount
                break

    total_bonded = sum(bonded_dict.values())

    return bonded_dict, total_bonded

async def get_NEPT_circulating_supply(client=None):
    """
    Get NEPT circulating supply from the API.
    Client parameter is optional to maintain compatibility with other function calls.
    """
    logger.info("Getting nept circulating supply")
    url = "https://api.nept.finance/v1/nept/circulating_supply"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            nept_circulating_supply = await response.text()
    
    # Try to convert to float for consistency
    try:
        return float(nept_circulating_supply)
    except ValueError:
        logger.warning(f"Warning: Could not convert circulating supply to float: {nept_circulating_supply}")
        return 0

async def get_nToken_circulating_supply(client=None):
    """
    Get nToken circulating supply values.
    Client parameter is optional to maintain compatibility with other function calls.
    """
    logger.info("Getting nTokens circulating supply")
    nTokens = ["natom","nusdt","nusdc","ninj","nweth","nausd","nsol","ntia"]
    url = "https://api.nept.finance/v1/supply/"
    nToken_circulating_supply = {}
    
    for nToken in nTokens:
        async with aiohttp.ClientSession() as session:
            async with session.get(url + nToken) as response:
                supply_text = await response.text()
                # Try to convert to float
                try:
                    nToken_circulating_supply[nToken] = float(supply_text)
                except ValueError:
                    logger.warning(f"Warning: Could not convert {nToken} supply to float: {supply_text}")
                    nToken_circulating_supply[nToken] = 0
                logger.info(f"nToken: {nToken}, Circulating Supply: {nToken_circulating_supply[nToken]}")
    
    return nToken_circulating_supply

async def get_lent_amount(client):
    logger.info("Getting lent amount")
    address = "inj1nc7gjkf2mhp34a6gquhurg8qahnw5kxs5u3s4u"
    query_data = '{"get_all_markets": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    lent_amounts = json.loads(decoded_data)
    #print(json.dumps(lent_amounts, indent=2))

    lent_amounts_dict = {}

    for market in lent_amounts:
        denom = market[0]["native_token"]["denom"]
        token_info = _get_token_info(denom)
        if token_info:
            decimals = int(token_info['decimals'])
            ticker = token_info['ticker']
            amount = float(market[1]["lending_principal"]) / 10**decimals
            #print(f"Denom: {denom}, Amount: {amount}, Ticker: {ticker}")
            lent_amounts_dict[ticker] = amount
    
    return lent_amounts_dict


async def get_borrowed_amount(client):
    logger.info("Getting borrowed amount")
    address = "inj1nc7gjkf2mhp34a6gquhurg8qahnw5kxs5u3s4u"
    query_data = '{"get_all_markets": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    borrowed_amounts = json.loads(decoded_data)
    #print(json.dumps(borrowed_amounts, indent=2))

    borrowed_amounts_dict = {}

    for market in borrowed_amounts:
        denom = market[0]["native_token"]["denom"]
        token_info = _get_token_info(denom)
        if token_info:
            decimals = int(token_info['decimals'])
            ticker = token_info['ticker']
            amount = float(market[1]["debt_pool"]["balance"]) / 10**decimals
            #print(f"Denom: {denom}, Amount: {amount}, Ticker: {ticker}")
            borrowed_amounts_dict[ticker] = amount
    
    return borrowed_amounts_dict

async def get_token_prices(client):
    logger.info("Getting token prices")
    address = "inj1u6cclz0qh5tep9m2qayry9k97dm46pnlqf8nre"

    token_prices_dict = {}
    tokens = _load_tokens()
    for token in tokens:
        denom = token['denom']
        token_type = token['token_type']
        ticker = token['ticker'] 
        if token_type == "native_token":
            query_data = '{"get_price": {"asset": {"native_token": {"denom": "' + denom + '"}}}}'
        else:
            query_data = '{"get_price": {"asset": {"token": {"contract_addr": "' + denom + '"}}}}'
        contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
        decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
        token_prices = json.loads(decoded_data)
        token_price = "$" + str(token_prices["price"])
        token_prices_dict[ticker] = token_price

    return token_prices_dict

async def get_nToken_contract_executes(client):
    logger.info("Getting nToken contract executes")
    nToken_contract_executes = {}
    tokens = _load_tokens()
    for token in tokens:
        contract_executes = None
        if token['token_type'] == "token":
            address = token['denom']
            contract_executes = await client.fetch_wasm_contract_by_address(address=address)

            if contract_executes and isinstance(contract_executes, dict) and "executes" in contract_executes:
                nToken_contract_executes[token['ticker']] = contract_executes["executes"]
            else:
                nToken_contract_executes[token['ticker']] = None

    return nToken_contract_executes

async def get_NEPT_staking_rates(client):
    logger.info("Getting NEPT staking rates")
    address = "inj1v3a4zznudwpukpr8y987pu5gnh4xuf7v36jhva"
    query_data = '{"get_params": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    pool_data = json.loads(decoded_data)

    emission_rate = float(pool_data["emission_rate"])/10**6
    
    # Access the reward weights from the bond_duration_settings list
    pool_1_reward_weight = float(pool_data["bond_duration_settings"][0][1]["reward_weight"])
    pool_2_reward_weight = float(pool_data["bond_duration_settings"][1][1]["reward_weight"])
    pool_3_reward_weight = float(pool_data["bond_duration_settings"][2][1]["reward_weight"])

    query_data = '{"get_state": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    staking_data = json.loads(decoded_data)

    pool_1_stake = float(staking_data["bonded"][0][1])/10**6
    pool_2_stake = float(staking_data["bonded"][1][1])/10**6
    pool_3_stake = float(staking_data["bonded"][2][1])/10**6

    average_yield = emission_rate / sum([pool_1_stake, pool_2_stake, pool_3_stake]) *100

    # Calculate effective stakes
    eff_stake_1 = pool_1_stake * pool_1_reward_weight
    eff_stake_2 = pool_2_stake * pool_2_reward_weight
    eff_stake_3 = pool_3_stake * pool_3_reward_weight

    total_eff_stake = eff_stake_1 + eff_stake_2 + eff_stake_3

    # Fraction of emission going to each pool
    fraction_1 = eff_stake_1 / total_eff_stake
    fraction_2 = eff_stake_2 / total_eff_stake
    fraction_3 = eff_stake_3 / total_eff_stake

    # Emission to each pool
    emission_pool_1 = emission_rate * fraction_1
    emission_pool_2 = emission_rate * fraction_2
    emission_pool_3 = emission_rate * fraction_3

    # Annual percentage rate (or daily, monthly, etc. depending on your timescale)
    apr_1 = str(round((emission_pool_1 / pool_1_stake) * 100,2))+"%"
    apr_2 = str(round((emission_pool_2 / pool_2_stake) * 100,2))+"%"
    apr_3 = str(round((emission_pool_3 / pool_3_stake) * 100,2))+"%"

    pool_yield_dict = {}
    pool_yield_dict["pool_1"] = apr_1
    pool_yield_dict["pool_2"] = apr_2
    pool_yield_dict["pool_3"] = apr_3
   
    return pool_yield_dict

async def get_NEPT_emission_rate(client):
    logger.info("Getting NEPT emission rate")
    address = "inj1v3a4zznudwpukpr8y987pu5gnh4xuf7v36jhva"
    query_data = '{"get_params": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    pool_data = json.loads(decoded_data)

    emission_rate = float(pool_data["emission_rate"])/10**6
    return emission_rate

async def get_collateral_amounts(client):
    logger.info("Getting collateral amounts")
    address = "inj1nc7gjkf2mhp34a6gquhurg8qahnw5kxs5u3s4u"
    query_data = '{"get_all_collaterals": {}}'
    contract_state = await client.fetch_smart_contract_state(address=address, query_data=query_data)
    decoded_data = base64.b64decode(contract_state["data"]).decode("utf-8")
    collaterals = json.loads(decoded_data)

    collaterals_dict = {}
    for collateral in collaterals:
        if "native_token" in collateral[0]:
            denom = collateral[0]["native_token"]["denom"]
        else:
            denom = collateral[0]["token"]["contract_addr"]
        token_info = _get_token_info(denom)
        if token_info:
            ticker = token_info['ticker']
            decimals = int(token_info['decimals'])
            amount = float(collateral[1]["collateral_pool"]["balance"]) / 10**decimals
            collaterals_dict[ticker] = amount
    return collaterals_dict

def _load_LP_pools():
    """Load LP pools from CSV file"""
    pools = []
    try:
        with open('LP_pools.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pools.append(row)
    except Exception as e:
        logger.error(f"Error loading LP pools: {e}")
    return pools

async def get_LP_info(client):
    logger.info("Getting LP info for all pools")
    url = "https://api.astroport.fi/api/pools/"
    pools_data = []
    
    # Load pool addresses from CSV
    pools = _load_LP_pools()
    if not pools:
        logger.error("No LP pools found in CSV file")
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            for pool in pools:
                pool_address = pool.get('LP_pool_address')
                if not pool_address:
                    logger.warning(f"Skipping pool with missing address: {pool}")
                    continue
                    
                try:
                    async with session.get(url + pool_address) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch LP info for pool {pool_address}. Status: {response.status}")
                            continue
                            
                        pool_info = await response.json()
                        
                        if not pool_info:
                            logger.error(f"Empty response from API for pool {pool_address}")
                            continue
                        
                        try:
                            # Get token symbols from the assets array
                            assets = pool_info.get("assets", [])
                            if not assets or len(assets) < 2:
                                logger.error(f"Invalid assets data for pool {pool_address}: {assets}")
                                continue
                                
                            token1 = assets[0].get("symbol", "Unknown")
                            token2 = assets[1].get("symbol", "Unknown")
                            
                            # Strip '.peggy' from token symbols if present
                            token1 = token1.replace('.peggy', '')
                            token2 = token2.replace('.peggy', '')
                            
                            LP_symbol = token1 + "/" + token2
                            
                            # Get liquidity and volume data
                            total_liquidity_usd = float(pool_info.get("totalLiquidityUSD", 0))
                            day_volume_usd = float(pool_info.get("dayVolumeUSD", 0))
                            day_LP_fees_usd = float(pool_info.get("dayLpFeesUSD", 0))
                            
                            # Get yield data
                            yield_data = pool_info.get("yield", {})
                            yield_total = float(yield_data.get("total", 0))*100
                            yield_pool_fees = float(yield_data.get("poolFees", 0))*100
                            yield_astro_rewards = float(yield_data.get("astro", 0))*100
                            yield_external_rewards = float(yield_data.get("externalRewards", 0))*100
                            
                            # Print the extracted information
                            print(f"\nPool: {LP_symbol}")
                            print(f"Total Liquidity (USD): ${total_liquidity_usd:,.2f}")
                            print(f"24h Volume (USD): ${day_volume_usd:,.2f}")
                            print(f"24h LP Fees (USD): ${day_LP_fees_usd:,.2f}")
                            print(f"Total Yield: {yield_total}%")
                            print(f"Pool Fees: {yield_pool_fees}%")
                            print(f"Astro Rewards: {yield_astro_rewards}%")
                            print(f"External Rewards: {yield_external_rewards}%")
                            

                            pools_data.append({
                                "LP_symbol": LP_symbol,
                                "pool_address": pool_address,
                                "total_liquidity_usd": total_liquidity_usd,
                                "day_volume_usd": day_volume_usd,
                                "day_LP_fees_usd": day_LP_fees_usd,
                                "yield_pool_fees": yield_pool_fees,
                                "yield_astro_rewards": yield_astro_rewards,
                                "yield_external_rewards": yield_external_rewards,
                                "yield_total": yield_total
                            })
                            
                        except (IndexError, KeyError, ValueError) as e:
                            logger.error(f"Error parsing pool info for {pool_address}: {str(e)}")
                            logger.error(f"Pool info structure: {json.dumps(pool_info, indent=2)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error fetching LP info for pool {pool_address}: {str(e)}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error in get_LP_info: {str(e)}")
        return None
        
    return pools_data

async def main() -> None:
    network = Network.mainnet()
    client = AsyncClient(network)
    lp_info = await get_LP_info(client)
    print(lp_info)

if __name__ == "__main__":
    asyncio.run(main())











