import datetime
from pydantic import BaseModel
import yaml
import json

from .utils import calculate_number_of_tokens, fmt_chat_details, fmt_msg_user_name
from .tools import get_tools, FunctionCall

from telebot import types as telebot_types
import database


class SystemPromptSchema(BaseModel):
    """
    Description of the agent's system prompt
    """

    # Role of the agent within the chat
    # Configurable by:
    # name - the username of the agent
    # date - the current date
    Role: str
    # The Stated Objective of the agent
    Objective: str
    # The tools available to the agent
    # Configurable by:
    # tools - a formatted list of tools available to the agent
    # tool_schema - json schema for calling tools
    # max_self_recurse_depth - the maximum depth of recursion the agent can use
    Tools: str


class PromptManager:
    """
    PromptManager is responsible for formatting prompts based on simple data types and schemas
    It should most definitely not be responsible for interacting with the model or application state
    """

    def __init__(self, agent_config: dict):
        # Chat ML Configuration
        self.user_prepend = agent_config["chat_ml"]["user_prepend"]
        self.user_append = agent_config["chat_ml"]["user_append"]
        self.stop_sequences = agent_config["chat_ml"]["stop_sequences"]
        self.line_separator = "\n"

        self.tools = get_tools()
        self.tool_schema = json.loads(FunctionCall.schema_json())
        self.max_self_recurse_depth = agent_config["agent"]["max_self_recurse_depth"]

        # Persona Configuration and Templates
        self.name = "chat-bot"
        with open(agent_config["agent"]["system_prompt_template"], "r") as f:
            yaml_content = yaml.safe_load(f)
            self.system_prompt_schema = SystemPromptSchema(
                Role=yaml_content.get("Role", ""),
                Objective=yaml_content.get("Objective", ""),
                Tools=yaml_content.get("Tools", ""),
            )

    def set_name(self, name: str):
        """
        Set the persona name for the chat bot
        """
        self.name = name

    def tool_message(self, tool_message: str) -> str:
        """
        Format a tool message into a proper chat log line
        - tool: the tool message to format
        Returns a string representing the chat log line
        """
        # NOTE: this is a lil hacky, but in every context we generate this message, we're appeninfing
        #  to a completed response, so add a user append at the beginning
        return f"{self.line_separator}{self.user_append}{self.line_separator}{self.user_prepend}tool{self.line_separator}{tool_message}{self.user_append}{self.line_separator}"

    def chat_message(self, message: telebot_types.Message | database.Message) -> str:
        """
        Format either a telebot message or a database message into a chat log line

        - message: the message to format -- either a telebot.types.Message or a database.Message

        Returns a string representing the chat log line
        """

        from_user_name = fmt_msg_user_name(message.from_user)
        is_reply = message.reply_to_message is not None

        sender = from_user_name
        if is_reply:
            to_user_name = fmt_msg_user_name(message.reply_to_message.from_user)
            sender = f"{from_user_name} (in reply to {to_user_name})"
        return f"{self.user_prepend}{sender}{self.line_separator}{message.text}{self.line_separator}{self.user_append}{self.line_separator}"

    def prompt_response(
        self,
        message: telebot_types.Message | database.Message | str | None = None,
        text: str = "",
        token_limit: int = 2048,
    ) -> tuple[str, int]:
        """
        Prompt a simple response from the model:
        - message: the message to prompt a response from (optional)
        - text: text to start the model off on (optional)
        - token_limit: the maximum number of tokens the prompt can use

        Returns a tuple of (prompt, used_tokens)
        """

        base = ""
        if message is not None and isinstance(
            message, (telebot_types.Message, database.Message)
        ):
            base = self.chat_message(message)
        elif message is not None and isinstance(message, str):
            base = message

        prompt = f"{base}{self.user_prepend}{self.name}{self.line_separator}{text}"

        used_tokens = calculate_number_of_tokens(prompt)

        if token_limit == -1:
            return prompt, used_tokens
        elif used_tokens > token_limit:
            raise Exception("prompt_response(): prompt exceeds token limit")

        return prompt, used_tokens

    def system_prompt(
        self,
        chat: telebot_types.Chat,
        token_limit: int = 2048,
    ) -> tuple[str, int]:
        """
        Build a system prompt for a specific chat

        - chat: the chat to build the system prompt for
        - token_limit: the maximum number of tokens the prompt can use

        Returns a tuple of (system_prompt, used_tokens)
        """

        # Format the date as a human readble string to give to the system
        # Day of the week, Month Day, Year @ Hour:Minute:Second
        # ex. "Monday, January 1, 2021 @ 12:00:00"
        date = datetime.datetime.now().strftime("%A, %B %d, %Y @ %H:%M:%S")
        variables = {
            "date": date,
            "name": self.name,
            "chat_details": fmt_chat_details(chat),
            "tools": self.tools,
            "tool_schema": self.tool_schema,
            "max_self_recurse_depth": self.max_self_recurse_depth,
        }

        system_prompt = ""
        for _, value in self.system_prompt_schema.dict().items():
            formatted_value = value.format(**variables)
            formatted_value = formatted_value.replace("\n", " ")
            system_prompt += f"{formatted_value}"

        system_prompt = f"{self.user_prepend}SYSTEM{self.line_separator}{system_prompt}{self.user_append}{self.line_separator}"

        # Update our used tokens count
        used_tokens = calculate_number_of_tokens(system_prompt)

        # Check if we're over our token limit
        if used_tokens > token_limit:
            raise Exception("build_system_prompt(): system prompt exceeds token limit")

        return system_prompt, used_tokens
