from telebot.types import Message

from src.config import config
from src.utils.telegram import get_mentions_in_message


async def text_message_handler(message: Message):
    """
    Handle all text messages.
    Use the agent to construct an informed response
    """
    # Logging setup
    span = config.LOGGER.get_span(message)
    span.info("Received text message")

    try:
        chat_id = message.chat.id

        # Add the message to the chat history
        await config.DATABASE.add_message(message, span=span)

        # Determine if the message is meant for the bot
        should_reply = False
        if message.chat.type == "private":
            # Always reply to DMs
            should_reply = True
        else:
            if (
                message.reply_to_message is not None
                and message.reply_to_message.from_user.username
                == config.BOT_INFO.username
            ):
                # The message is a reply to a message that is the bot
                should_reply = True

            mentions = get_mentions_in_message(message)
            if f"@{config.BOT_INFO.username}" in mentions:
                # Message is mentioning the bot
                should_reply = True

        if should_reply is False:
            span.info("Message not intended for the bot")

        # Send an initial response
        # TODO: select a phrase randomly from a list to get a more dynamic result
        result = "I'm thinking..."
        reply = await config.BOT.reply_to(message, result)

        # TODO: Implement rendering logic here based on the code and content
        # Attempt to reply to the message
        try:
            async for content in config.AGENT.yield_response(
                message, config.DATABASE, span
            ):  # TODO: not defined
                # Check for an updated response, otherwise just do nothing
                if content != result:
                    result = content
                    # Update the message
                    reply = await config.BOT.edit_message_text(
                        chat_id=chat_id, message_id=reply.message_id, text=result
                    )
        except Exception as e:
            # Attempt to edit the message to indicate an error
            reply = await config.BOT.edit_message_text(
                chat_id=message.chat.id,
                message_id=reply.message_id,
                text="I'm sorry, I got confused. Please try again.",
            )
            # Raise the error up to our handler
            raise e
        finally:
            # Attempt to update the message history to reflect the final response
            await config.DATABASE.add_message(
                reply, use_edit_date=True, reply_to_message_id=message.message_id
            )

    except Exception as e:
        span.error(f"Error handling text message: {e}")
    finally:
        return None
