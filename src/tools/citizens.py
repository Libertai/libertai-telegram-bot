
import aiohttp

metadata_base_url = "https://aleph.sh/vm/bd8291cca9a3de79937c452a606d81efc912ab7d223cd88031da5ca5e2a868dd/QmVpCmKPnD3dAFK61WE5czz7ucV3GHuqHqNsj2wNfWVjXf"


async def get_citizen_information(number: int) -> dict:
    """
    Get the information of a citizen
    Args:
        number: The citizen number
    Returns:
        The information of the citizen as a JSON object
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{metadata_base_url}/{number}") as response:
            return await response.json()