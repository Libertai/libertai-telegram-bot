import requests
import yfinance as yf

from typing import List
from duckduckgo_search import DDGS
from langchain.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool


@tool
def duckduckgo_search_text(query: str) -> dict:
    """
    Search DuckDuckGo for the top result of a given text query.
    Use when probing for general information, or when a user requests a web search.
    Args:
        query (str): The query to search for.
    Returns:
        dict: the top 5 results from DuckDuckGo. If an error occurs, an exception is returns within the "error" key.
    """
    try:
        search = DDGS()
        results = search.text(query, max_results=5)
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}


@tool
def duckduckgo_search_answer(query: str) -> dict:
    """
    Search DuckDuckGo for the top answer of a given question.
    Use when trying to answer a specific question that is outside the scope of the model's knowledge base.
    Args:
        query (str): The question to search for.
    Returns:
        dict: the top answer from DuckDuckGo. If an error occurs, an exception is returns within the "error" key.
    """
    try:
        search = DDGS()
        results = search.answers(query)
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_current_stock_price(symbol: str) -> float | None:
    """
    Get the current stock price for a given symbol.

    Args:
      symbol (str): The stock symbol.

    Returns:
      float: The current stock price, or None if an error occurs.
    """
    try:
        stock = yf.Ticker(symbol)
        # Use "regularMarketPrice" for regular market hours, or "currentPrice" for pre/post market
        current_price = stock.info.get(
            "regularMarketPrice", stock.info.get("currentPrice")
        )
        return current_price if current_price else None
    except Exception as _e:
        return None


@tool
def get_current_cryptocurrency_price_usd(symbol: str) -> dict | None:
    """
    Get current price of a cryptocurrency in USD.

    Args:
        symbol (str): The non-truncated cryptocurrency name to get the price of in USD (e.g. "bitcoin", "ethereum", "solana", "aleph", etc.).

    Returns:
        dict: The price of the cryptocurrency in the form {"coin": {"usd": <price>}}, or None if an error occurs.
    """

    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    )
    response = requests.get(url)
    if response.status_code == 200:
        output = response.json()
        # CoinGecko returns an empty dictionary if the coin doesn't exist -- fun :upside_down_face:
        if output == {}:
            return None
        return output
    else:
        return None


def get_tools() -> List[dict]:
    """
    Get our available tools as OpenAPI-compatible tools
    """

    # Register Functions Here
    functions = [
        duckduckgo_search_text,
        duckduckgo_search_answer,
        get_current_stock_price,
        get_current_cryptocurrency_price_usd,
    ]

    tools = [convert_to_openai_tool(f) for f in functions]
    return tools
