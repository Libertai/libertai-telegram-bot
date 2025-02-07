import telebot.types as telebot_types
from libertai_agents.interfaces.messages import Message as LibertaiMessage
from libertai_agents.interfaces.messages import MessageRoleEnum

from src.config import config
from src.utils.telegram import (
    get_formatted_message_content,
    get_formatted_username,
    should_reply_to_message,
)

# Max number of messages we will pass
MESSAGES_NUMBER = 50


async def text_message_handler(message: telebot_types.Message):
    """
    Handle all text messages.
    Use the agent to construct an informed response
    """
    # Logging setup
    span = config.LOGGER.get_span(message)
    span.info("Received text message")

    reply: telebot_types.Message | None

    try:
        chat_id = message.chat.id

        # Add the message to the chat history
        await config.DATABASE.add_message(message, span=span)

        should_reply = should_reply_to_message(message)
        if should_reply is False:
            span.info("Message not intended for the bot")

        # Send an initial response
        # TODO: select a phrase randomly from a list to get a more dynamic result
        result = "I'm thinking..."
        reply = await config.BOT.reply_to(message, result)

        messages: list[LibertaiMessage] = []

        chat_history = await config.DATABASE.get_chat_last_messages(
            chat_id, MESSAGES_NUMBER, span=span
        )
        # Iterate over the messages we've pulled
        for chat_msg in reversed(chat_history):
            message_username = get_formatted_username(chat_msg.from_user)
            message_content = get_formatted_message_content(chat_msg)
            # TODO: support multiple users with names
            role = (
                MessageRoleEnum.assistant
                if message_username == get_formatted_username(config.BOT_INFO)
                else MessageRoleEnum.user
            )
            messages.append(LibertaiMessage(role=role, content=message_content))

        # TODO: pass system prompt with chat details
        async for response_msg in config.AGENT.generate_answer(
            messages,
            system_prompt="You are a helpful assistant. If the first line of a message contains something like 'username (in reply to other_user)', it's an information useful for you, but you should not reproduce this in your answer, just respond with your answer.",
        ):
            if response_msg.content != result:
                result = response_msg.content
                # Update the message
                reply = await config.BOT.edit_message_text(
                    chat_id=chat_id, message_id=reply.message_id, text=result
                )

    except Exception as e:
        span.error(f"Error handling text message: {e}")
        # Attempt to edit the message to indicate an error

        if reply is not None:
            reply = await config.BOT.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text="I'm sorry, I got confused. Please try again.",
            )
    finally:
        # Attempt to update the message history to reflect the final response
        if reply is not None:
            await config.DATABASE.add_message(
                reply, use_edit_date=True, reply_to_message_id=message.message_id
            )
        return None
