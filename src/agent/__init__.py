import aiohttp
import time

from telebot import types as telebot_types

from .utils import calculate_number_of_tokens
from .tools import ToolExecutor
from .prompt_manager import PromptManager
from database import AsyncDatabase
from logger import MessageSpan


class Agent:
    """
    A Chat Bot that generates informed prompts based on the current conversation history.
    """

    def __init__(self, agent_config: dict):
        # Instance Configuration
        self.model_name = agent_config["model"]["name"]
        self.model_api_url = agent_config["model"]["api_url"]
        self.model_engine = agent_config["model"]["engine"]

        # Model Parameters
        self.max_completion_tokens = agent_config["model"]["max_completion_tokens"]
        self.max_prompt_tokens = agent_config["model"]["max_prompt_tokens"]
        self.temperature = agent_config["model"]["temperature"]
        self.sampler_order = agent_config["model"]["sampler_order"]
        self.top_p = agent_config["model"]["top_p"]
        self.top_k = agent_config["model"]["top_k"]
        self.stop_sequences = agent_config["chat_ml"]["stop_sequences"]

        # Agent Behavior
        self.max_completion_tries = agent_config["agent"]["max_completion_tries"]
        self.max_self_recurse_depth = agent_config["agent"]["max_self_recurse_depth"]

        # Initialize an empty Map to track open context slots on the server
        self.model_chat_slots = {}
        # Initialize the Tool Executor
        self.tool_executor = ToolExecutor()
        # Initialize the Prompt Manager
        self.prompt_manager = PromptManager(agent_config)

    # State Helpers

    def name(self):
        """
        Return the name of the chat bot
        """
        return self.prompt_manager.name

    def set_name(self, name: str):
        """
        Set the persona name for the chat bot
        """
        self.prompt_manager.set_name(name)

    async def clear_chat(self, chat_id: str):
        """
        Clear the chat from the model's available context
        """
        if chat_id in self.model_chat_slots:
            session, _ = self.model_chat_slots[chat_id]
            await session.close()
            del self.model_chat_slots[chat_id]

    async def clear_all_chats(self):
        """
        Close all open sessions
        """
        for session, _ in self.model_chat_slots.values():
            await session.close()
        self.model_chat_slots = {}

    # Where the magic happens

    async def build_prompt(
        self,
        message: telebot_types.Message,
        database: AsyncDatabase,
        span: MessageSpan,
        batch_size: int = 10,
        offset: int = 1,
    ) -> tuple[str, int]:
        """
        Build the most up to date prompt for the chat given the current conversation history.
        Max out at `token_limit` tokens.

        - chat: the chat to build the log for
        - token_limit: the maximum number of tokens the log can use
        - batch_size: the number of messages to pull at a time
        """

        # Keep track of how many tokens we're using
        used_tokens = 0
        token_limit = self.max_prompt_tokens

        chat = message.chat
        chat_id = chat.id

        # Generate our system prompt
        system_prompt, system_prompt_tokens = self.prompt_manager.system_prompt(
            message.chat, token_limit=token_limit
        )

        # Generate our agent prompt for the model to complete on
        prompt_response, prompt_response_tokens = self.prompt_manager.prompt_response(
            message=message, token_limit=token_limit - system_prompt_tokens
        )

        # Now start filling in the chat log with as many tokens as we can
        basic_prompt_tokens = system_prompt_tokens + prompt_response_tokens
        used_tokens += basic_prompt_tokens
        chat_log_lines = []
        offset = 1
        done = False
        try:
            # Keep pulling messages until we're done or we've used up all our tokens
            while not done and used_tokens < token_limit:
                # Get `batch_size` messages from the chat history
                messages = await database.get_chat_last_messages(
                    chat_id, batch_size, offset, span=span
                )
                # Construct condition on whether to break due to no more messages
                # If set we won't re-enter the loop
                done = messages is None or len(messages) < batch_size

                # Iterate over the messages we've pulled
                for message in messages:
                    line = self.prompt_manager.chat_message(message)
                    # Calculate the number of tokens this line would use
                    additional_tokens = calculate_number_of_tokens(line)

                    # Break if this would exceed our token limit before appending to the log
                    if used_tokens + additional_tokens > token_limit:
                        done = True
                        # Break out of the for loop.
                        # Since we're 'done' we won't continue the while loop
                        break

                    # Update our used tokens count
                    used_tokens += additional_tokens

                    # Actually append the line to the log
                    chat_log_lines.append(line)

                # Update our offset
                offset += batch_size

            # Now build our prompt in reverse
            chat_log = ""
            for line in reversed(chat_log_lines):
                chat_log = f"{chat_log}{line}"

            return f"{system_prompt}{chat_log}{prompt_response}", used_tokens
        except Exception as e:
            # Log the error, but return the portion of the prompt we've built so far
            span.warn(
                f"Agent::build_prompt(): error building prompt: {str(e)}. Returning partial prompt."
            )
            return f"{system_prompt}{prompt_response}", basic_prompt_tokens

    async def complete(
        self, prompt: str, chat_id: int, span: MessageSpan
    ) -> tuple[str, int]:
        """
        Complete on a prompt against our model within a given number of tries.

        Returns a str containing the prompt's completion.
        """

        if chat_id in self.model_chat_slots:
            session, slot_id = self.model_chat_slots[chat_id]
        else:
            session = aiohttp.ClientSession()
            slot_id = -1

        params = {
            "prompt": prompt,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        # Update the parameters based on the model engine
        if self.model_engine == "llamacpp":
            params.update(
                {
                    "n_predict": self.max_completion_tokens,
                    # NOTE: for now just set both of these
                    "id_slot": slot_id,
                    "slot_id": slot_id,
                    "typical_p": 1,
                    "tfs_z": 1,
                    "stop": self.stop_sequences,
                    "cache_prompt": True,
                    "use_default_badwordsids": False,
                }
            )
        else:
            raise Exception("Agent::complete(): unsupported model engine")

        max_tries = self.max_completion_tries
        tries = 0
        errors = []
        compounded_result = ""
        last_result = ""
        while tries < max_tries:
            span.debug(
                f"Agent::complete(): attempt: {tries} | slot_id: {slot_id}",
            )
            span.debug(
                f"Agent::complete(): compounded result: {compounded_result}",
            )
            # Append the compound result to the prompt
            params["prompt"] = f"{params['prompt']}{last_result}"
            try:
                async with session.post(self.model_api_url, json=params) as response:
                    if response.status == 200:
                        # Read the response
                        response_data = await response.json()

                        # Get the slot id from the response
                        if "id_slot" in response_data:
                            slot_id = response_data["id_slot"]
                        elif "slot_id" in response_data:
                            slot_id = response_data["slot_id"]
                        self.model_chat_slots[chat_id] = session, slot_id

                        # Determine if we're stopped
                        stopped = (
                            response_data["stopped_eos"]
                            or response_data["stopped_word"]
                        )
                        last_result = response_data["content"]
                        compounded_result = f"{compounded_result}{last_result}"
                        token_count = calculate_number_of_tokens(compounded_result)
                        # If we're stopped, return the compounded result
                        if stopped:
                            return compounded_result, token_count
                        # Otherwise, check if we've exceeded the token limit, and return if so
                        elif token_count > self.max_completion_tokens:
                            span.warn("Agent::complete(): Exceeded token limit")
                        return compounded_result, token_count
                    else:
                        raise Exception(
                            f"Agent::complete(): Non 200 status code: {response.status}"
                        )
            except Exception as e:
                span.warn(f"Agent::complete(): Error completing prompt: {str(e)}")
                errors.append(e)
            finally:
                tries += 1
        # If we get here, we've failed to complete the prompt after max_tries
        raise Exception(f"Agent::complete(): Failed to complete prompt: {errors}")

    # TODO: split out the response yielding from rendering the response
    async def yield_response(
        self, message: telebot_types.Message, database: AsyncDatabase, span: MessageSpan
    ):
        """
        Yield a response from the agent given it's current state and the message it's responding to.

        Yield a string containing the response.
        """
        start = time.time()
        span.info("Agent::yield_response()")

        chat_id = message.chat.id
        max_self_recurse_depth = self.max_self_recurse_depth

        # Build the prompt
        prompt, used_tokens = await self.build_prompt(message, database, span)

        span.info(f"Agent::yield_response(): prompt used tokens: {used_tokens}")
        span.debug("Agent::yield_response(): prompt built: " + prompt)

        try:
            # Keep track of the tokens we've seen out of completion
            completion_tokens = 0
            # Keep track of the tokens we generate from the completion
            recursive_tokens = 0
            # Keep track of the depth of self recursion
            self_recurse_depth = 0
            while self_recurse_depth < max_self_recurse_depth:
                # Complete and determine the tokens used
                completion, used_tokens = await self.complete(prompt, chat_id, span)
                completion_tokens += used_tokens

                span.debug("Agent::yield_response(): completion: " + completion)

                tool_message = None
                try:
                    # Attempt to parse a tool call from the completion
                    tool_message = self.tool_executor.handle_completion(
                        completion, self_recurse_depth, span
                    )

                    span.debug(
                        f"Agent::yield_response(): tool_message: {tool_message}",
                    )
                except Exception as e:
                    span.warn(
                        "Error handling tools message: " + str(e),
                    )
                    raise e
                finally:
                    # If ther's nothing to do, return the completion
                    if tool_message is None:
                        total_time = time.time() - start
                        # Log
                        # - completion tokens -- how many tokens the model generated
                        # - recursive tokens -- how many tokens we generated due to recursion
                        # - depth -- how deep we recursed
                        # - time -- how long we spent
                        span.info(
                            f"Agent::yield_response(): completion tokens: {completion_tokens} | recursive tokens: {recursive_tokens} | depth: {self_recurse_depth} | time: {total_time}"
                        )
                        yield completion
                        return

                    self_recurse_depth += 1

                    if self_recurse_depth >= max_self_recurse_depth:
                        span.warn(
                            "Agent::yield_response(): Function call depth exceeded",
                        )
                        raise Exception("Function call depth exceeded")

                    # Build up the new prompt and recurse
                    tool_message = self.prompt_manager.tool_message(tool_message)
                    # Keep track of the tokens we generate from the tool message
                    recursive_tokens += calculate_number_of_tokens(tool_message)

                    # TODO: I should probably check that the token limit isn't exceeded here
                    # For now, just let it go through no matter how big the recursion gets
                    prompt, _ = self.prompt_manager.prompt_response(
                        f"{prompt}{completion}{tool_message}", token_limit=-1
                    )

                    span.debug(
                        f"Agent::yield_response(): continuing recursion on prompt: {prompt}"
                    )

                    yield "Gathering some more information to help you better..."
        except Exception as e:
            raise e
