from telebot.types import Message


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
