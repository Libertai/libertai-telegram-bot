import json
import ast
# import xml.etree.ElementTree as ET



def parse_json_garbage(s):
    s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return json.loads(s[:e.pos])


def validate_and_extract_tool_calls(agent_response):
    validation_result = False
    tool_calls = []
    error_message = None

    # Extract JSON data
    try:
        json_data = parse_json_garbage(agent_response)
        if 'arguments' and 'name' in json_data:
            tool_calls.append(json_data)
            validation_result = True
    except Exception as e:
        # error_message = f"Cannot extract JSON data: {e}"
        pass

    # try:
    #     # wrap content in root element
    #     xml_root_element = f"<root>{agent_response}</root>"
    #     root = ET.fromstring(xml_root_element)

    #     # extract JSON data
    #     for element in root.findall(".//tool_call"):
    #         json_data = None
    #         try:
    #             json_text = element.text.strip()
    #             try:
    #                 # Prioritize json.loads for better error handling
    #                 json_data = json.loads(json_text)
    #             except json.JSONDecodeError as json_err:
    #                 try:
    #                     # Fallback to ast.literal_eval if json.loads fails
    #                     json_data = ast.literal_eval(json_text)
    #                 except (SyntaxError, ValueError) as eval_err:
    #                     error_message = (
    #                         f"JSON parsing failed with both json.loads and ast.literal_eval:\n"
    #                         f"- JSON Decode Error: {json_err}\n"
    #                         f"- Fallback Syntax/Value Error: {eval_err}\n"
    #                         f"- Problematic JSON text: {json_text}"
    #                     )
    #                     continue
    #         except Exception as e:
    #             error_message = f"Cannot strip text: {e}"

    #         if json_data is not None:
    #             tool_calls.append(json_data)
    #             validation_result = True

    # except ET.ParseError as err:
    #     error_message = f"XML Parse Error: {err}"

    # Return default values if no valid data is extracted
    return validation_result, tool_calls, error_message
