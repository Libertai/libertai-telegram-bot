import sys
import nltk

from telebot import types as telebot_types

sys.path.append("..")
import database


def calculate_number_of_tokens(line: str):
    """
    Determine the token length of a line of text
    """
    tokens = nltk.word_tokenize(line)
    return len(tokens)


def fmt_chat_details(chat: telebot_types.Chat, line_separator="\n"):
    """
    Construct appropriate chat details for the model prompt

    Errors:
        If the provided chat is neither a private nor group chat.
    """

    # TODO: some of these are only called on .getChat, these might not be available. Verify!
    if chat.type in ["private"]:
        return f"""Private Chat Details:{line_separator}Username: {chat.username or ""}{line_separator}First Name: {chat.first_name or ""}{line_separator}Last Name: {chat.last_name or ""}{line_separator}Bio: {chat.bio or ""}"""

    elif chat.type in ["group", "supergroup"]:
        return f"""Group Chat Details:{line_separator}Title: {chat.title or ""}{line_separator}Description: {chat.description or ""}{line_separator}Members: {chat.active_usernames or ""}"""
    else:
        raise Exception("chat_details(): chat is neither private nor group")


def fmt_msg_user_name(user: database.User | telebot_types.User):
    """
    Determine the appropriate identifier to which associate a user with
    the chat context
    """
    return user.username or ((user.first_name or "") + " " + (user.last_name or ""))
