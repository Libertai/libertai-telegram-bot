from telebot.types import Message

from src.config import config


async def help_command_handler(message: Message):
    """
    Send a message to the user with a list of commands and their descriptions.
    """
    # Log the command
    span = config.LOGGER.get_span(message)
    span.info("/help command called")
    try:
        # Send the message to the user
        help_text = "The following commands are available:\n\n"
        for command, description in config.BOT_COMMANDS:
            help_text += f"/{command} - {description}\n"
        await config.BOT.reply_to(message, help_text)
    except Exception as e:
        span.error(f"Error handling /help command: {e}")
    finally:
        return None
