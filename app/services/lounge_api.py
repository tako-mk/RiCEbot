import aiohttp

BASE_URL = "https://lounge.mkcentral.com"

# mkworld lounge 個人データ取得
async def fetch_player(discord_id: int, game="mkworld", season=None):
    params = {
        "discordId": str(discord_id),
        "game": game
    }
    if season is not None:
        params["season"] = season

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/player", params=params) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

# mkworld lounge mmr取得
async def fetch_mmr(discord_id: int, game="mkworld"):
    data = await fetch_player(discord_id, game)
    if not data:
        return None
    return data.get("mmr")

# mkworld lounge peak取得
async def fetch_peak(discord_id: int, game="mkworld"):
    data = await fetch_player(discord_id, game)
    if not data:
        return None
    return data.get("maxMmr")
