import asyncio
from telebot import types as telebot_types, async_telebot

from database import AsyncDatabase
from logger import Logger
from agent import Agent
from config import Config

## Configuration Constants ##

# Telegram Chat Commands
# NOTE: regardless of what commands you write, they will not be accessible to the user unless you register them here!
BOT_COMMANDS = [
    ("help", "Show the help menu"),
    ("clear", "Clear the chat history from the chat bot"),
]

## State ##
CONFIG = Config()
LOGGER = Logger(CONFIG.log_path, CONFIG.debug)

try:
    LOGGER.info("Setting up Bot...")
    BOT = async_telebot.AsyncTeleBot(CONFIG.tg_token)
    LOGGER.info("Setting up AsyncDatabase...")
    DATABASE = AsyncDatabase(CONFIG.database_path)
    LOGGER.info("Setting up Agent...")
    AGENT = Agent(CONFIG.agent_config)
except Exception as e:
    LOGGER.error(f"An unexpected error occurred during setup: {e}")
    raise e

## State Management ##


# Set the bot's actual name and all of the potential names it might be called
def set_bot_name(name: str):
    # Set the name of the bot on the agent -- this is it's telegram username and persona name
    AGENT.set_name(name)
    # Common monikers for the chat bot or what one might call it
    #  We'll use this as a base to build a simple response filter
    names = [
        "chatbot",
        "chat-bot",
        "chat bot",
        "chatbot",
        "chat-bot",
        "chat bot",
        "bot",
        "assistant",
        "ai",
    ]

    names.append(name)
    bot_names = []
    for n in names:
        bot_names.extend(
            [
                n,
                n.lower(),
                n.upper(),
                # bunch of potential misspellings
                n.replace(" ", ""),
                n.replace("-", ""),
                n.replace(" ", "-"),
                n.replace("-", " "),
                n.replace(" ", "_"),
                n.replace("_", " "),
                n.replace("_", "-"),
                n.replace("-", "_"),
                # Missing letters at the edges of words
                n[1:],
                n[:-1],
                # apped letters at the edges of words
                n[1:] + n[0],
                n[-1] + n[:-1],
            ]
        )
    global BOT_NAMES
    BOT_NAMES = bot_names


## Handlers ##

# Command Handlers


@BOT.message_handler(commands=["help"])
async def help_command_handler(message: telebot_types.Message):
    """
    Send a message to the user with a list of commands and their descriptions.
    """
    # Log the command
    span = LOGGER.get_span(message)
    span.info("/help command called")
    try:
        # Send the message to the user
        help_text = "The following commands are available:\n\n"
        for command, description in BOT_COMMANDS:
            help_text += f"/{command} - {description}\n"
        await BOT.reply_to(message, help_text)

        # Ok
        return None
    except Exception as e:
        span.error(f"Error handling /help command: {e}")
        return None


@BOT.message_handler(commands=["clear"])
async def clear_command_handler(message: telebot_types.Message):
    """
    Clear the history of messages for a given chat.
    """
    # Log the command
    span = LOGGER.get_span(message)
    span.info("/clear command called")
    try:
        # Send an ACK to the user
        reply = await BOT.reply_to(message, "Clearing chat history...")

        # Clear the chat history from the database and the agent
        chat_id = message.chat.id
        await DATABASE.clear_chat_history(chat_id)
        await AGENT.clear_chat(chat_id)

        # Send a message to the user acknowledging the clear
        await BOT.edit_message_text(
            chat_id=chat_id,
            message_id=reply.message_id,
            text="Chat history cleared.",
        )

        # Ok
        return None
    except Exception as e:
        span.error(f"Error handling /clear command: {e}")
        return None


# Message Type Handlers


@BOT.message_handler(content_types=["text"])
async def text_message_handler(message: telebot_types.Message):
    """
    Handle all text messages.
    Use the agent to construct an informed response
    """
    # Log the message
    span = LOGGER.get_span(message)
    span.info("Received text message")
    reply = None
    try:
        chat_id = message.chat.id

        # Add the message to the chat history
        await DATABASE.add_message(message, span=span)

        # Determine if the message is meant for the bot
        # If the message is not a private message, check if the message mentions the bot
        if message.chat.type not in ["private"]:
            # Don't let the bot respond to messages which don't mention the bot
            found = False
            for target in BOT_NAMES:
                if target in message.text:
                    found = True
                    break
            if not found:
                return None
            # TODO: does this ever get triggered?
            # Don't let the bot respond to messages that are replies to itself
            if (
                message.reply_to_message is not None
            ) and message.reply_to_message.from_user.username == AGENT.name():
                return None

        # Send an initial response
        result = "I'm thinking..."
        reply = await BOT.reply_to(message, result)

        # TODO: Implement rendering logic here based on the code and content
        # Attempt to reply to the message
        try:
            async for content in AGENT.yield_response(message, DATABASE, span):
                # Check for an updated response, otherwise just do nothing
                if content != result:
                    result = content
                    # Update the message
                    reply = await BOT.edit_message_text(
                        chat_id=chat_id, message_id=reply.message_id, text=result
                    )
        except Exception as e:
            # Attempt to edit the message to indicate an error
            reply = await BOT.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text="I'm sorry, I got confused. Please try again.",
            )
            # Raise the error up to our handler
            raise e
        finally:
            # Attempt to update the message history to reflect the final response
            await DATABASE.add_message(
                reply, use_edit_date=True, reply_to_message_id=message.message_id
            )
    except Exception as e:
        span.error(f"handle_text_message(): Error handling text message: {e}")
        if reply is None:
            await BOT.reply_to(message, "I'm sorry, I got confused. Please try again.")
    finally:
        return None


async def register_bot_commands():
    """
    Register the commands with the bot so that they are accessible to the user through the menu
    """
    await BOT.set_my_commands(
        [
            telebot_types.BotCommand(command, description)
            for command, description in BOT_COMMANDS
        ],
        scope=telebot_types.BotCommandScopeDefault(),
    )


async def run():
    LOGGER.info("Starting Bot...")
    try:
        # Get the bot's user name and set the perosna name
        bot_info = await BOT.get_me()
        LOGGER.info(f"Bot started: {bot_info.username}")
        set_bot_name(bot_info.username)
        await register_bot_commands()
        await BOT.polling()
    except Exception as e:
        LOGGER.error(f"An unexpected error occurred: {e}")
    finally:
        LOGGER.info("Stopping Bot...")
        # Close all open connections
        await AGENT.clear_all_chats()


if __name__ == "__main__":
    asyncio.run(run())
