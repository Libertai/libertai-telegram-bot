import logging
import os
from logging import FileHandler, LogRecord, StreamHandler

from telebot import types as telebot_types


# Log Formatter
# Used to trace events that span the handling of a message within a chat
class LogFormatter(logging.Formatter):
    def format(self, record: LogRecord):
        new_record = record

        if hasattr(record, "chat_id"):
            new_record.chat_id = record.chat_id
        else:
            # This should never happen, but if it does, we'll just set the chat ID to N/A
            new_record.chat_id = "N/A"

        if hasattr(record, "message_id"):
            new_record.message_id = record.message_id
        else:
            # This should never happen, but if it does, we'll just set the message ID to N/A
            new_record.message_id = "N/A"

        return super().format(new_record)


class Logger:
    logger: logging.Logger

    def __init__(self, log_path: str | None = None, debug: bool = False):
        """
        Initialize a new Log instance
        - log_path - where to send output. If `None` logs are sent to the console
        - debug - whether to set debug level
        """

        # Create the logger
        logger = logging.getLogger(__name__)
        # Set the log formatter
        formatter = LogFormatter(
            "%(asctime)s - %(levelname)s - CHAT %(chat_id)s - MSG %(message_id)s - %(message)s"
        )

        # Set our debug mode
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            # Hide debug logs from other libraries
            logging.getLogger("asyncio").setLevel(logging.WARNING)
            logging.getLogger("aiosqlite").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)

            # Tool libraries
            logging.getLogger("yfinance").setLevel(logging.WARNING)
            logging.getLogger("peewee").setLevel(logging.WARNING)

        else:
            logging.basicConfig(level=logging.INFO)

        handler: FileHandler | StreamHandler
        # Set where to send logs
        if log_path is not None and log_path.strip() != "":
            # Create parent directories if they don't exist
            log_path = log_path.strip()
            log_dir = os.path.dirname(log_path)
            os.makedirs(log_dir, exist_ok=True)
            handler = logging.FileHandler(log_path)
            handler.setFormatter(formatter)
        else:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)

        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False

        self.logger = logger

    def get_span(self, message: telebot_types.Message):
        return MessageSpan(self, message.chat.id, message.message_id)

    def warn(
        self,
        message: str,
        chat_id: int | None = None,
        message_id: int | None = None,
    ):
        extra = {}
        if chat_id:
            extra["chat_id"] = chat_id
        if message_id:
            extra["message_id"] = message_id
        self.logger.warning(message, extra=extra)

    def debug(
        self,
        message: str,
        chat_id: int | None = None,
        message_id: int | None = None,
    ):
        extra = {}
        if chat_id:
            extra["chat_id"] = chat_id
        if message_id:
            extra["message_id"] = message_id

        self.logger.debug(message, extra=extra)

    def info(
        self,
        message: str,
        chat_id: int | None = None,
        message_id: int | None = None,
    ):
        extra = {}
        if chat_id:
            extra["chat_id"] = chat_id
        if message_id:
            extra["message_id"] = message_id

        self.logger.info(message, extra=extra)

    def error(
        self,
        message: str,
        chat_id: int | None = None,
        message_id: int | None = None,
    ):
        extras = {}
        if chat_id:
            extras["chat_id"] = chat_id
        if message_id:
            extras["message_id"] = message_id

        self.logger.error(message, extra=extras)


class MessageSpan:
    def __init__(self, logger: Logger, chat_id: int, message_id: int):
        self.logger = logger
        self.chat_id = chat_id
        self.message_id = message_id

    def warn(self, message: str):
        self.logger.warn(message, chat_id=self.chat_id, message_id=self.message_id)

    def debug(self, message: str):
        self.logger.debug(message, chat_id=self.chat_id, message_id=self.message_id)

    def info(self, message: str):
        self.logger.info(message, chat_id=self.chat_id, message_id=self.message_id)

    def error(self, message: str):
        self.logger.error(message, chat_id=self.chat_id, message_id=self.message_id)
