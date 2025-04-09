import asyncio
from queries import search_transaction_by_hash
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network

async def main():
    try:
        network = Network.mainnet()
        client = AsyncClient(network)
        print(f"Searching for transaction hash: A475DEB2BD59B5A1345F47F0FF3BC20E42206E2A07413F33A89DAD85A5A2D4D2")
        await search_transaction_by_hash(client, 'A475DEB2BD59B5A1345F47F0FF3BC20E42206E2A07413F33A89DAD85A5A2D4D2')
        # No need to close the client as it doesn't have a close method
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 