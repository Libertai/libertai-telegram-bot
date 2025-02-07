import requests
import yfinance  # type: ignore


def get_current_stock_price(symbol: str) -> float | None:
    """
    Get the current stock price for a given symbol.

    Args:
      symbol: The stock symbol.

    Returns:
      The current stock price, or None if an error occurs.
    """
    try:
        stock = yfinance.Ticker(symbol)
        # Use "regularMarketPrice" for regular market hours, or "currentPrice" for pre- or post-market
        current_price = stock.info.get(
            "regularMarketPrice", stock.info.get("currentPrice")
        )
        return current_price if current_price else None  # type: ignore
    except Exception as _e:
        return None


def get_current_cryptocurrency_price_usd(symbol: str) -> dict | None:
    """
    Get current price of a cryptocurrency in USD.

    Args:
        symbol: The non-truncated cryptocurrency name to get the price of in USD (e.g. "bitcoin", "ethereum", "solana", "aleph", etc.).

    Returns:
        The price of the cryptocurrency in a dict of the form {"coin": {"usd": <price>}}, or None if an error occurs.
    """

    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    )
    response = requests.get(url)
    if response.status_code == 200:
        output = response.json()
        # CoinGecko returns an empty dictionary if the coin doesn't exist
        if output == {}:
            return None
        return output
    else:
        return None
