import os

from dotenv import load_dotenv
from libertai_agents.agents import ChatAgent
from libertai_agents.models import get_model
from telebot import async_telebot
from telebot.async_telebot import AsyncTeleBot
from telebot.types import User

from src.utils.database import AsyncDatabase
from src.utils.logger import Logger


class _Config:
    BOT_COMMANDS: list[tuple[str, str]]
    LOGGER: Logger
    BOT: AsyncTeleBot
    DATABASE: AsyncDatabase
    AGENT: ChatAgent

    # Data that will be set at the beginning of the agent loop and shouldn't be used before
    BOT_INFO: User

    def __init__(self):
        load_dotenv()

        self.BOT_COMMANDS = [
            ("help", "Show the help menu"),
            ("clear", "Clear the chat history from the chat bot"),
        ]

        # Logger
        log_path = os.getenv("LOG_PATH")
        debug = os.getenv("DEBUG", "False") == "True"
        self.LOGGER = Logger(log_path, debug)

        try:
            # Bot
            self.LOGGER.info("Setting up bot...")
            token = os.getenv("TELEGRAM_TOKEN")
            self.BOT = async_telebot.AsyncTeleBot(token, parse_mode="MARKDOWN")

            # Database
            self.LOGGER.info("Setting up database...")
            database_path = os.getenv("DATABASE_PATH", ":memory:")
            self.DATABASE = AsyncDatabase(database_path)

            # LibertAI Agent
            self.LOGGER.info("Setting up agent...")
            self.AGENT = ChatAgent(
                model=get_model("NousResearch/Hermes-3-Llama-3.1-8B"),
                system_prompt="You are a helpful assistant",
                tools=[],
                expose_api=False,
            )
        except Exception as e:
            self.LOGGER.error(f"An unexpected error occurred during setup: {e}")
            raise e

        # TODO: check if below variables are still required
        # searchapi_token = os.getenv("SEARCHAPI_TOKEN")
        # self.searchapi_token = searchapi_token


config = _Config()
