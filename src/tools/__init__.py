from libertai_agents.interfaces.tools import Tool

from src.tools.finance import (
    get_current_cryptocurrency_price_usd,
    get_current_stock_price,
)

tools: list[Tool] = [
    Tool.from_function(get_current_stock_price),
    Tool.from_function(get_current_cryptocurrency_price_usd),
]
