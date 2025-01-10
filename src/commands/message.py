import telebot.types as telebot_types
from libertai_agents.interfaces.messages import Message as LibertaiMessage
from libertai_agents.interfaces.messages import MessageRoleEnum
import aiohttp

from src.config import config
from src.utils.telegram import (
    get_formatted_message_content,
    get_formatted_username,
    should_reply_to_message,
)

# Max number of messages we will pass
MESSAGES_NUMBER = 50

CHAT_SESSIONS = {}


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
            return None

        # Send an initial response
        # TODO: select a phrase randomly from a list to get a more dynamic result
        result = "I'm thinking..."
        reply = await config.BOT.reply_to(message, result)

        context = await config.KNOWLEDGEBASE.query(message.text, min=0.25, top_k=2)

        messages: list[LibertaiMessage] = []

        chat_history = await config.DATABASE.get_chat_last_messages(
            chat_id, MESSAGES_NUMBER, span=span
        )
        # Iterate over the messages we've pulled
        for chat_msg in reversed(chat_history):
            message_username = get_formatted_username(chat_msg.from_user)
            message_role, message_content = get_formatted_message_content(chat_msg)
            # TODO: support multiple users with names
            role = (
                MessageRoleEnum.assistant
                if message_username == get_formatted_username(config.BOT_INFO)
                else MessageRoleEnum.user
            )
            messages.append(LibertaiMessage(role=role, content=message_content))

        for title, content, similarity in context:
            messages.append(LibertaiMessage(role=MessageRoleEnum.system, content=f"Relevant knowledgebase entry: {title}\n{content}"))
            

        if chat_id not in CHAT_SESSIONS:
            CHAT_SESSIONS[chat_id] = aiohttp.ClientSession()

        # TODO: pass system prompt with chat details when libertai-agents new version released
        # and also tell it to answer directly (to avoid including "username in reply to username" in its answer)
        async for response_msg in config.AGENT.generate_answer(messages, session=CHAT_SESSIONS[chat_id]):
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
