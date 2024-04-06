import os
from os import sys

from .validator import (
    validate_function_call_schema,
)
from .utils import (
    validate_and_extract_tool_calls,
)
from .functions import (
    get_tools,
)

# NOTE: the sys path append is necessary to import the functions module
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
import functions


class ToolExecutor:
    def __init__(self):
        self.tools = get_tools()

    def process_completion_and_validate(self, completion):
        validation, tool_calls, error_message = validate_and_extract_tool_calls(
            completion
        )

        if validation:
            return tool_calls, error_message
        else:
            tool_calls = None
            return tool_calls, error_message

    def execute_function_call(self, tool_call):
        function_name = tool_call.get("name")
        function_to_call = getattr(functions, function_name, None)
        function_args = tool_call.get("arguments", {})

        if not function_to_call:
            raise ValueError(f"Function {function_name} not found")

        function_response = function_to_call(*function_args.values())
        results_dict = f'{{"name": "{function_name}", "content": {function_response}}}'
        return results_dict

    def handle_completion(
        self, completion: str, depth: int, span, line_separator="\n"
    ) -> str | None:
        try:
            tool_calls, error_message = self.process_completion_and_validate(completion)
            tool_message = "Current call depth: " + str(depth) + line_separator
            if tool_calls:
                for tool_call in tool_calls:
                    validation, message = validate_function_call_schema(
                        tool_call, self.tools
                    )
                    if validation:
                        span.info(
                            f"Function call {tool_call.get('name')} is valid | arguments: {tool_call.get('arguments')}"
                        )
                        try:
                            function_response = self.execute_function_call(tool_call)
                            tool_message += f"<tool_response>{line_separator}{function_response}{line_separator}</tool_response>{line_separator}"
                            span.info(
                                f"Function call {tool_call.get('name')} executed successfully with response: {function_response}"
                            )
                        except Exception as e:
                            span.error(
                                f"Error executing function call {tool_call.get('name')}: {e}"
                            )
                            tool_name = tool_call.get("name")
                            tool_message += f"<tool_response>{line_separator}There was an error when executing the function: {tool_name}{line_separator}Here's the error traceback: {e}{line_separator}Please call this function again with correct arguments within XML tags <tool_call></tool_call>{line_separator}</tool_response>{line_separator}"
                    else:
                        span.warn(f"Function call {tool_call.get('name')} is invalid")
                        tool_name = tool_call.get("name")
                        tool_message += f"<tool_response>{line_separator}There was an error validating function call against function signature: {tool_name}{line_separator}Here's the error traceback: {message}{line_separator}Please call this function again with correct arguments within XML tags <tool_call></tool_call>{line_separator}</tool_response>{line_separator}"
                return tool_message
            elif error_message:
                span.error(f"Error parsing function calls: {error_message}")
                tool_message += f"<tool_response>{line_separator}There was an error parsing function calls{line_separator}Here's the error stack trace: {error_message}{line_separator}Please call the function again with correct syntax within XML tags <tool_call></tool_call>{line_separator}</tool_response>{line_separator}"
                return tool_message
            return None
        except Exception as e:
            raise e
