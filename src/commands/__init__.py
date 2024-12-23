from telebot.types import BotCommand, BotCommandScopeDefault, Message

from src.commands.clear import clear_command_handler
from src.commands.help import help_command_handler
from src.commands.message import text_message_handler
from src.config import config


async def register_commands():
    """
    Register the Telegram commands with the bot so that they are accessible to the user through the menu
    """
    await config.BOT.set_my_commands(
        [
            BotCommand(command, description)
            for command, description in config.BOT_COMMANDS
        ],
        scope=BotCommandScopeDefault(),
    )


# Define the message and command handlers


@config.BOT.message_handler(commands=["help"])
async def help_command(msg: Message):
    result = await help_command_handler(msg)
    return result


@config.BOT.message_handler(commands=["clear"])
async def clear_command(msg: Message):
    result = await clear_command_handler(msg)
    return result


@config.BOT.message_handler(content_types=["text"])
async def text_message(msg: Message):
    result = await text_message_handler(msg)
    return result
