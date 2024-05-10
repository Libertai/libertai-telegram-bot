import requests
import collections.abc
#hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping

from hyper.contrib import HTTP20Adapter

import yfinance as yf

from typing import List
from duckduckgo_search import DDGS
from langchain.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool


from config import Config
CONFIG = Config()

@tool
def google_search(query):
    """ Search google results. 
    Args:
        query (str): The query to search for.
    Returns:
        list: A list of dictionaries containing the title, link, snippet, and other information about the search results."""

    r = requests.get("https://www.searchapi.io/api/v1/search",
                     params = {
                         "q": query,
                         "engine": "google",
                         "api_key": CONFIG.searchapi_token
                         })
    
    results = r.json()
    organic_results = results.get("organic_results")
    for result in organic_results:
        if "favicon" in result:
            del result["favicon"]
        if "snippet_highlighted_words" in result:
            del result["snippet_highlighted_words"]
    return organic_results

@tool
def duckduckgo_get_answer(query):
    """ Get an answer from DuckDuckGo's Instant Answer API.
    Args:
        query (str): The query to search for.
    Returns:
        dict: A dictionary containing the answer, answer type, abstract, abstract source, abstract URL, definition, definition source, definition URL, and image.
    """

    session = requests.Session()
    session.mount('https://', HTTP20Adapter())
    r = session.get("https://api.duckduckgo.com",
                     params = {
                         "q": query,
                         "format": "json",
                         "no_html": 1,
                         "skip_disambig": 1
                         })
    output = r.json()
    print(output)
    return {
        "answer": output.get("Answer"),
        "answer_type": output.get("AnswerType"),
        "abstract": output.get("Abstract"),
        "abstract_text": output.get("AbstractText"),
        "abstract_source": output.get("AbstractSource"),
        "abstract_url": output.get("AbstractURL"),
        "definition": output.get("Definition"),
        "definition_source": output.get("DefinitionSource"),
        "definition_url": output.get("DefinitionURL"),
        "image": output.get("Image"),
    }


# @tool
# def duckduckgo_search_text(query: str) -> dict:
#     """
#     Search DuckDuckGo for the top result of a given text query.
#     Use when probing for general information, or when a user requests a web search.
#     Args:
#         query (str): The query to search for.
#     Returns:
#         dict: the top 5 results from DuckDuckGo. If an error occurs, an exception is returns within the "error" key.
#     """
#     try:
#         search = DDGS()
#         results = search.text(query, max_results=5)
#         return {"results": results}
#     except Exception as e:
#         return {"error": str(e)}


# @tool
# def duckduckgo_search_answer(query: str) -> dict:
#     """
#     Search DuckDuckGo for the top answer of a given question.
#     Use when trying to answer a specific question that is outside the scope of the model's knowledge base.
#     Args:
#         query (str): The question to search for.
#     Returns:
#         dict: the top answer from DuckDuckGo. If an error occurs, an exception is returns within the "error" key.
#     """
#     try:
#         search = DDGS()
#         results = search.answers(query)
#         return {"results": results}
#     except Exception as e:
#         return {"error": str(e)}


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

@tool
def get_cryptocurrency_info(symbol: str) -> dict | None:
    """
    Get the informations about a cryptocurrency. It includes where it's listed,
    in what categories it is, the socials urls (twitter, telegram, homepage...), the market data as well in USD (includes information like the market cap, price, atl, ath...).
    """

    url = (
        f"https://api.coingecko.com/api/v3/coins/{symbol}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
    )
    response = requests.get(url)
    if response.status_code == 200:
        output = response.json()
        if 'market_data' in output:
            # let's keep only the usd price on all values that have currencies inside market_data
            for key, value in output['market_data'].items():
                if isinstance(value, dict):
                    if 'usd' in value:
                        output['market_data'][key] = value['usd']
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
        # duckduckgo_search_text,
        # duckduckgo_search_answer,
        google_search,
        duckduckgo_get_answer,
        get_current_stock_price,
        get_current_cryptocurrency_price_usd,
        get_cryptocurrency_info
    ]

    tools = [convert_to_openai_tool(f) for f in functions]
    return tools
