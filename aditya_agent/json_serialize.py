from google.adk.agents import LlmAgent, SequentialAgent

import logging
import warnings

from dotenv import load_dotenv

load_dotenv()

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
text_to_json_agent = LlmAgent(
    name="TextToJsonAgent",
    model="gemini-2.0-flash",
    instruction="""
    You are an AI that converts the given well-formatted text data into JSON format.
    Output only the JSON string representing the data AND NOTHING ELSE (No prefixes or suffixes).
    Text Input:
    {test_case}
    """,
    output_key="json_output"
)

# Optional Validation Agent
json_validation_agent = LlmAgent(
    name="JsonValidationAgent",
    model="gemini-2.0-flash",
    instruction="""
    Validate the following JSON data. If valid, output OK, else provide error details.
    JSON Input:
    {json_output}
    """,
    output_key="validation_result"
)

# Optional Formatter Agent (if restructuring is needed)
json_formatter_agent = LlmAgent(
    name="JsonFormatterAgent",
    model="gemini-2.0-flash",
    instruction="""
    Format or correct the JSON data based on validation feedback.
    JSON Input:
    {json_output}
    Validation Feedback:
    {validation_result}
    Output the improved JSON string.
    """,
    output_key="final_json_output"
)

sub_agent_text_to_json = SequentialAgent(
    name="TextToJsonPipeline",
    sub_agents=[text_to_json_agent, json_validation_agent, json_formatter_agent],
)