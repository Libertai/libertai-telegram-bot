import os

from dotenv import load_dotenv


class _Config:
    TELEGRAM_TOKEN: str
    DATABASE_PATH: str
    DEBUG: bool
    LOG_PATH: str | None

    def __init__(self):
        load_dotenv()

        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

        # Set the Database URL, default to in-memory for now
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", ":memory:")

        debug = os.getenv("DEBUG", "True")
        self.DEBUG = debug == "True"

        self.LOG_PATH = os.getenv("LOG_PATH")

        # TODO: check if below variables are still required
        # searchapi_token = os.getenv("SEARCHAPI_TOKEN")
        # self.searchapi_token = searchapi_token


config = _Config()
