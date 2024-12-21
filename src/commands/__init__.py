from telebot.types import BotCommand, BotCommandScopeDefault, Message

from src.commands.clear import clear_command_handler
from src.commands.help import help_command_handler
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


# Define the command handlers


@config.BOT.message_handler(commands=["help"])
async def help_command(message: Message):
    result = await help_command_handler(message)
    return result


@config.BOT.message_handler(commands=["clear"])
async def clear_command(message: Message):
    result = await clear_command_handler(message)
    return result
