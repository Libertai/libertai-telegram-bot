from telebot.types import Message, User


def get_mentions_in_message(message: Message) -> list[str]:
    """Returns an array of mentions inside the text of a message. Each mention is in the format '@username'"""
    mentions: list[str] = []

    if message.entities is None:
        return mentions
    for entity in message.entities:
        if entity.type == "mention":
            mention_text = message.text[entity.offset : entity.offset + entity.length]
            mentions.append(mention_text)
    return mentions


def get_formatted_username(user: User) -> str:
    """
    Determine the appropriate identifier to which associate a user with
    the chat context
    """
    return user.username or f'{user.first_name or ""} {user.last_name or ""}'


def get_formatted_message_content(message: Message) -> str:
    """
    Format either a telebot message into a string representing its content
    """
    sender = get_formatted_username(message.from_user)
    is_reply = message.reply_to_message is not None

    if is_reply:
        reply_to_username = get_formatted_username(message.reply_to_message.from_user)
        sender = f"{sender} (in reply to {reply_to_username})"

    return f"{sender}\n{message.text}"
