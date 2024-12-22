from telebot.types import Message

from src.config import config


async def clear_command_handler(message: Message):
    """
    Clear the history of messages for a given chat.
    """
    # Log the command
    span = config.LOGGER.get_span(message)
    span.info("/clear command called")
    try:
        # Send an ACK to the user
        reply = await config.BOT.reply_to(message, "Clearing chat history...")

        # Clear the chat history from the database and the agent
        chat_id = message.chat.id
        await config.DATABASE.clear_chat_history(chat_id)

        # Send a message to the user acknowledging the clear
        await config.BOT.edit_message_text(
            chat_id=chat_id,
            message_id=reply.message_id,
            text="Chat history cleared.",
        )
    except Exception as e:
        span.error(f"Error handling /clear command: {e}")
    finally:
        return None
