import sys
import os
import asyncio
import time
import json

import logging
import warnings
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, create_model
from google.adk.agents.callback_context import CallbackContext

from typing import List, Dict, Optional, Any, Callable, AsyncGenerator
from typing_extensions import override

from google.adk.agents import (
    LlmAgent, 
    SequentialAgent, 
    LoopAgent, 
    BaseAgent,
    InvocationContext
)

from json_serialize import sub_agent_text_to_json

from google.adk.agents.parallel_agent import (
    _create_branch_ctx_for_sub_agent, 
    _merge_agent_run,
    _merge_agent_run_pre_3_11
)

from google.adk.models import BaseLlm

from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.tool_context import ToolContext
from google.adk.utils.context_utils import Aclosing
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)

load_dotenv()

class DataFormat(Enum):
    json = "json"
    csv = "csv"
    xml = "xml"
    word = "word"

Tool = tuple[Callable[..., Any], Any, Any]

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-pro")

#Defining the env variables

CREATOR_AGENT = os.getenv("CREATOR_AGENT", "gemini-2.5-pro")
FORMAT_VALIDATION_AGENT = os.getenv("FORMAT_VALIDATION_AGENT", "gemini-2.5-pro")
DATA_VALIDATION_AGENT = os.getenv("DATA_VALIDATION_AGENT", "gemini-2.5-pro")

#Defining the basic agents

def get_instruction(instruction_string: str, state_key: str) -> str:
    state_key = '{'+state_key+'}'
    return instruction_string.replace("{state_key}", state_key)

mapping = {"test_case_agent":"data_set_agent", "data_set_agent": "results"}

class SIMDAgent(BaseAgent):
    """
    Parallel agent to process different data points following the same instructions.
    This does not allow subagent, since it performs a single task.

    Extra Attributes:
        data_points (Dict[str, Any]): The list of data points to process.
        instruction_agent_type (BaseAgent): The type of instruction agent to use.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow"
    }

    model: str | BaseLlm
    instruction: str  
    tools: Optional[list[Tool]] = None
    # data_points: Dict[str, Any]
    # instruction_agent_type: BaseAgent
    sub_agents_dict: Dict[str, BaseAgent] = {}

    def __init__(
        self,
        name: str,
        model: str = "gemini-2.5-pro",
        description: str = "",
        instruction: str = "",
        tools: Optional[list[Tool]] = None,
        instruction_agent_type: BaseAgent = LlmAgent,
        data_points: Dict[str, Any] = {}
    ):
        sub_agents = []
        sub_agents_dict = {}
        print(f"Model : {model}, Name : {name}")
        for key, value in data_points.items():
            print(f"Key: {key}, Value: {value}")
            if not isinstance(value, dict):
                raise ValueError(
                    f"Data point {key} has unsupported type {type(value)}. Supported types are str, int, float, bool, list, dict."
                )
            worker_agent = instruction_agent_type(
                name=f"{key}",
                model=model,
                description=description,
                instruction=get_instruction(instruction, f"{key}"),
                tools=tools,
                output_key=f"{key.replace(name,mapping.get(name,name))}",
            )
            print(f"Created sub-agent: {worker_agent.name} with key : {key} and output key {key.replace(name,mapping.get(name,name))}")
            sub_agents_dict[key] = worker_agent
            sub_agents.append(worker_agent)

        super().__init__(
            name=name, 
            model=model, 
            description=description, 
            instruction=instruction, 
            tools=tools or [],
            sub_agents=[],
            sub_agents_dict=sub_agents_dict,
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        for key1, sub_agent1 in self.sub_agents_dict.items():
            print(f"Running agent {self.name}, key {key1} with problematic results {ctx.session.state.get('problematic_results', [])}, with sub_agents_dict keys {list(self.sub_agents_dict.keys())} and {key1[len(self.name):]} and len is {len(self.name)}")
        agent_runs = [
            sub_agent1.run_async(
                _create_branch_ctx_for_sub_agent(self, sub_agent1, ctx)
            )
            for key1, sub_agent1 in self.sub_agents_dict.items() if key1[len(self.name)+1:] in ctx.session.state.get('problematic_results', [])
        ]

        print(f"The agents run are for {self.name} {agent_runs}")
        try:
            if sys.version_info >= (3, 11):
                async with Aclosing(_merge_agent_run(agent_runs)) as agen:
                    async for event in agen:
                        yield event
            else:
                async with Aclosing(_merge_agent_run_pre_3_11(agent_runs)) as agen:
                    async for event in agen:
                        yield event
        finally:
            for sub_agent_run in agent_runs:
                await sub_agent_run.aclose()

TEST_CREATION_PROMPT = """Change the provided compliance clause into a rigid test caset that adhers strictly to the mentioned points in the clause. 

The compliance clause created should be technically accurate. Mention them poitwise.
Here is the compliance clause :
{state_key}
"""

DATA_SET_CREATION_PROMPT = """Using the following provied test case data for a compilance system . 
    {state_key} 

    Create a set of data that can be used exhaustively to verify against the test case. Provide the following in the response :
    ** (1) Any required set of columns for the data set that might be needed for test creation. **
    ** (2) An integer providing a number for the number of data points created ( Choose number of data points wisely so that the all the edge cases for data set are handled)**
    ** (3) Corresponding to each data point, provide relevant paramters that were decided in the first step. Also as a final paramter provide the anwer whether according to the test case
    the data point passes or fails the test case. **

    For example.
    Consider the following test case :
    The system shall maintain an immutable audit trail of all patient data access events, including user ID, timestamp, and action performed.

    We will provide the following parameters for the data set :
    Test Case ID	User ID	Timestamp	Action	Modification Attempt	Expected Compliance Result

    Number of data points : 2

    Here are example data points : 

    Test Case ID	User ID	Timestamp	Action	Modification Attempt	Expected Compliance Result
    TC-001	         clinician_001	     READ      2025-09-12T10:15:22Z		No	    Pass
    TC-004	         NULL	             READ      2025-09-12T10:18:00Z		No	    Fail

    Note : This example is not exhaustive testing since it missses some required edge cases like Missing Timestamp, Missing Action etc.

    STRICTLY Design the data set in the required format and make sure it is exhaustive and covers all edge cases.
"""

initial_input = {'test_case_agent_5.1.5.1.1': {'titles': ['PROJECT ORGANISATION', 'Project Organisation Structure'], 'compliance': 'A project organisation is set up to champion, manage and execute an IT project.  Members \nof the project organisation include the Project Owner, Project Steering Committee (PSC), \nProject Assurance Team (PAT), Internal Project Manager (IPM) and Business Analyst \n(BA). \n \nThe PSC champions the project and is the ultimate decision-maker for the project.  It \nprovides steer and support for the IPM and endorses acceptance of project deliverables. \nThe IPM manages the project and monitors the project implementation on a day-to-day \nbasis for the Project Owner/the PSC. \n \nThe PAT is responsible for overseeing project progress and managing quality assurance \nactivities, which include: \n(a) recommending the test plans, test specifications and test summary report for \nendorsement by the PSC; and \n(b) co-ordinating, monitoring and resolving priority conflicts on the testing activities to \nensure smooth running of testing activities.  \n \nPlease refer to the Practice Guide to Project Management for IT Projects under an \nOutsourced Environment (PGPM) for more details of the project organisation.'}, 'test_case_agent_5.1.5.1.2': {'titles': ['PROJECT ORGANISATION', 'Test Group'], 'compliance': 'Testing is the process of executing a program with the intent of finding errors.  Since it is \nsuch a destructive process, it may be more effective and successful if the testing is \nperformed by an independent third party other than the original system analysts / \nprogrammers. \n \nAs far as possible, testing should be performed by a group of people different from those \nperforming design and coding of the same system.  That group of people is called the Test \nGroup. \n \nA Test Group can be set up to carry out the testing activities especially for large-scale \nprojects or projects involving a large number of users.  The emphasis here is on the \nindependent role of the Test Group, which does not necessarily mean dedicated resources.  \nThe necessity of an independent Test Group should be determined at the project \ninitialisation stage through an assessment based on project complexity, criticality, \nimplementation schedule and other risks.  The type(s) of testing to be performed \n\n \nOVERVIEW \n________________________________________________________________________________ \n \n_______________________________________________________________________________ \n \n    5-2 \n  \nindependently and the high level estimation of additional resources, if required, should be \ndetermined and planned for respectively as early as possible. \n \nThe following figure shows an example of project organisation with the formation of a \nTest Group and an optional Independent Testing Contractor providing independent testing \nservice.   It is noted that the independent testing may be conducted by a Test Group of in-\nhouse staff members as well as by external contractor.  \n \n \n \nFigure 1 - Example of Project Organisation with Test Group and Independent \nTesting Contractor'}, 'test_case_agent_5.2': {'titles': ['TESTING ACTIVITIES'], 'compliance': 'With reference to the Agile Software Development Method, test preparation should be \nstarted as early as possible and constant communication should be maintained with \nrelevant stakeholders to facilitate collaboration and transparency.  The following activities \nare suggested: \n \n(i) \nThe IPM should develop a high level test plan covering all major test types during \nproject initiation with the objectives, scope of testing and the composition of Test \nGroup including contractors, business users and internal IT staff with defined \nroles and responsibilities. \n \n(ii) \nContractor project manager (or IPM for in-house developed project) to enrich the \ntest plans by engaging his/her staff to draft test cases; internal IT staff to check all \nmajor test plans; and business users to provide different test cases to address \ndifferent scenarios; and \n\n \nOVERVIEW \n________________________________________________________________________________ \n \n_______________________________________________________________________________ \n \n    5-3 \n  \n \n(iii) Contractor project manager (or IPM for in-house developed project) to maintain \nongoing communication and collaboration among stakeholders by distributing all \nmajor test plans and feedbacks to stakeholders regularly to keep them informed \nthe project progress throughout the whole system development stage. \n \nA computer system is subject to testing from the following five different perspectives: \n \n(i) \nTo validate individual program modules against program specifications (Unit \nTesting); \n \n(ii) \nTo validate linkages or interfaces between program modules against design \nspecifications (Link/Integration Testing); \n \n(iii) To validate integrated software against functional specifications (Function \nTesting); \n \n(iv) To validate the integrated software against specifications on operating \nenvironment (System Testing); and, \n \n(v) \nTo validate the integrated software against end-user needs and business \nrequirements (Acceptance Testing). \n \n(Refer to Section 7) \n\n \nOVERVIEW \n________________________________________________________________________________ \n \n_______________________________________________________________________________ \n \n    5-4'}, 'test_case_agent_5.3': {'titles': ['TEST DOCUMENTATION'], 'compliance': 'To document testing activities through the use of \n \n(i) \nTest Plan \n(ii) \nTest Specification \n(iii) \nTest Incident Report \n(iv) \nTest Progress Report \n(v) \nTest Summary Report \n \n(Refer to Section 8)'}, 'test_case_agent_5.4.5.4.1': {'titles': ['TEST PLANNING AND CONTROL', 'Progress Control'], 'compliance': 'Monitor the day-to-day progress of the testing activities through the use of Test Progress \nReports. \n \n(Refer to Section 8.5)'}, 'test_case_agent_5.4.5.4.2': {'titles': ['TEST PLANNING AND CONTROL', 'Quality Control / Assurance'], 'compliance': 'Testing documentation to be compiled by Test Group or Independent Testing Contractor \nif outsourced, cross-checked by quality assurance staff2, and reviewed by the PAT.'}, 'test_case_agent_5.4.5.4.3': {'titles': ['TEST PLANNING AND CONTROL', 'Resource Estimation'], 'compliance': 'Project teams may update the testing metrics information to a centralised database for \nfuture test planning references. \n \n                                                 \n2 Quality assurance staff should be the IPM or other delegated staff.  However, those who are the members of the Test \nGroup should not take up the quality assurance role for the project if the tests are conducted by them but not by \nIndependent Testing Contractor. \n\n \nGENERAL CONCEPTS \n \nOF TESTING \n________________________________________________________________________________ \n \n_______________________________________________________________________________'}}
initial_input = {'test_case_agent_5.1.5.1.1': {'titles': ['PROJECT ORGANISATION', 'Project Organisation Structure'], 'compliance': 'A project organisation is set up to champion, manage and execute an IT project.  Members \nof the project organisation include the Project Owner, Project Steering Committee (PSC), \nProject Assurance Team (PAT), Internal Project Manager (IPM) and Business Analyst \n(BA). \n \nThe PSC champions the project and is the ultimate decision-maker for the project.  It \nprovides steer and support for the IPM and endorses acceptance of project deliverables. \nThe IPM manages the project and monitors the project implementation on a day-to-day \nbasis for the Project Owner/the PSC. \n \nThe PAT is responsible for overseeing project progress and managing quality assurance \nactivities, which include: \n(a) recommending the test plans, test specifications and test summary report for \nendorsement by the PSC; and \n(b) co-ordinating, monitoring and resolving priority conflicts on the testing activities to \nensure smooth running of testing activities.  \n \nPlease refer to the Practice Guide to Project Management for IT Projects under an \nOutsourced Environment (PGPM) for more details of the project organisation.'}}
initial_input = {key.replace('.', '_'): value for key, value in initial_input.items()}
print(initial_input.keys())
new_dict = {key.replace('test_case_', 'data_set_'): value for key, value in initial_input.items()}
print(new_dict.keys())


problematic_results = []
for key in list(initial_input.keys()):
    problematic_results.append(key[len("test_case_agent_"):])
print(f"Initial problematic results: {problematic_results}, the type is {type(problematic_results)}")
problematic_results = list(problematic_results)
feedback = "The results for clause 5.1.5.1.2 dont look right, rest looks good"
feedback = ""

validation_prompt = f"""
 Based on the following feedback, identify which data points are still problematic:

Feedback: {feedback}\n\n""" + """
Original Input was this """ + "{original_input}" + """

Return only the list of problematic data point keys.

'If there is no problematic data points, or if feedback mentioned nothing to modfiy, call the exit_loop tool to exit the iteration.'
"""

validation_prompt = "Always call exit_loop at invocation"

test_case_creation_agent = SIMDAgent(
    name="test_case_agent",
    model=MODEL_NAME,
    instruction=TEST_CREATION_PROMPT,
    description="Create test_case based on user provied compliace clause",
    data_points=initial_input,
    tools=[],
    instruction_agent_type=LlmAgent,
)

data_set_creation_agent = SIMDAgent(
    name="data_set_agent",
    model=MODEL_NAME,
    instruction=DATA_SET_CREATION_PROMPT,
    description="Create a data set based on the provided test case, strictly maintain the format mentioned in the input",
    data_points=new_dict,
    tools=[],
    instruction_agent_type=LlmAgent,
)

count = 0

agent_response_test_case = {}
agent_response_data_set = {}

def exit_loop(tool_context:ToolContext) -> Dict[Any,Any]:
  """Call this function ONLY when the critique indicates no further changes are needed, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")

  for attr in dir(tool_context):
    print(f"    [Tool Context] {attr}: {getattr(tool_context, attr)}")

  print(f"Inovocation Context State: {tool_context.state.to_dict()}")

  response_dict = tool_context.state.to_dict()

  for key, value in response_dict.items():
    pass

async def serialize_and_save_responses(tool_context: ToolContext) -> None:
    """
    Serializes responses using the JSON serialization agent and saves them to individual files.
    
    Args:
        tool_context (ToolContext): The tool context containing the state and responses
    """
    session_service = InMemorySessionService()
    response_dict = tool_context.state.to_dict()

    print(f"The response dict is {response_dict}")

    list_keys = list(response_dict.keys())
    print(f"The list of keys are {list_keys} and type is {type(list_keys)}")

    for key in list_keys:
        print(f"Encoutnered key {key}")

        if "results_" not in key and "data_set_" not in key:
            print(f"Skipping key {key} as it is not relevant for serialization")
            continue

        value = response_dict[key]

        print(f"Preparing json file for data point: {key} with value: {value}")
            
        # Create a session for this value
        session = await session_service.create_session(
            app_name="json_serializer",
            user_id="user_id_123",
            session_id=f"json_session_{key}",
            state={"test_case": str(value)}  # Convert value to string for processing
        )

        # Create content for the agent
        content = types.Content(
            role='user',
            parts=[types.Part(text="Serialize the provided value to JSON format.")]
        )

        # Create runner with JSON serialization agent
        runner = Runner(
            agent=sub_agent_text_to_json,
            app_name="json_serializer",
            session_service=session_service
        )

        # Process the value
        async for event in runner.run_async(
            user_id="user_id_123",
            session_id=f"json_session_{key}",
            new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                json_output = event.content.parts[0].text
                print(f"The so called json output for key {key} is {json_output}")
                dict_output = session.state
                print(f"The keys are {dict_output.keys()}")
                print(f"The state output is {dict_output.get("final_json_output")}")
            
                # Save to file named after the key
                output_filename = f"{key}.json"
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"Saved JSON output to {output_filename}")

feedback_counter = 1

def take_feedback(callback_context: CallbackContext) -> Dict[Any, Any]:
    print(f"  [Tool Call] take_feedback triggered")
    global feedback, feedback_counter
    watch_directory: str = "."
      
    timeout: int = 300
    poll_interval: float = 1.0

    feedback_filename = f"feedback_{feedback_counter}.json"
    print(f"  Polling for file '{feedback_filename}' in '{watch_directory}'...")
    
    feedback_path = os.path.join(watch_directory, feedback_filename)
    start_time = time.time()

    print(f"  Watching for feedback file at path: {os.path.abspath(feedback_path)}")
    
    while time.time() - start_time < timeout:
        if os.path.exists(feedback_path):
            try:
                print(f"  Found feedback file: {feedback_path}")
                feedback = ""
                time.sleep(0.5)
                
                with open(feedback_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                is_feedback_present = data.get("is_feedback_present", False)
                if is_feedback_present is True:
                    content = f"Feedback was present and the content is {data.get('feedback', '')}"
                else:
                    content = "No feedback was provided"

                feedback = content
                
                print(f"  Successfully read feedback file with {len(content)} characters")
                feedback_counter += 1
                # return {
                #     "status": "success",
                #     "feedback": content,
                #     "source": "file_polling"
                # }
                return types.Content(
                    parts=[types.Part(text=f"Obtained feedback content {content}")],
                    role="user"
                )
            except Exception as e:
                print(f"  Error reading feedback file: {e}")
                # return {
                #     "status": "error",
                #     "error": f"Failed to read feedback file: {e}"
                # }
                return types.Content(
                    parts=[types.Part(text=f"Obtained no feedback content. Call exit_loop")],
                    role="user"
                )
        
        time.sleep(poll_interval)
    
    print(f"  Timeout: No feedback file found within {timeout} seconds")
    # return {
    #     "status": "timeout",
    #     "error": f"No feedback found within {timeout} seconds"
    # }
    return types.Content(
        parts=[types.Part(text=f"Obtained No feedback content. Call exit_loop")],
        role="user"
    )

async def exit_loop(tool_context: ToolContext) -> Dict[Any, Any]:
    """
    Call this function ONLY when the critique indicates no further changes are needed.
    Now includes JSON serialization of responses.
    """
    print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    
    tool_context.actions.escalate = True
    await serialize_and_save_responses(tool_context)
    return {}

validation_agent = LlmAgent(
    name="validation_agent",
    model=FORMAT_VALIDATION_AGENT,
    before_agent_callback=take_feedback,
    tools=[exit_loop],
    instruction=validation_prompt,
    output_key="problematic_results",
)

creator_agent = LoopAgent(
    name="creator_agent",
    max_iterations=5,
    sub_agents=[
        test_case_creation_agent,
        data_set_creation_agent,
        validation_agent
    ]
)

# root_agent = SequentialAgent(
#     name="root_agent",
#     sub_agents=[
#         creator_agent,
#         data_set_creation_agent
#     ]
# )

async def main():
    session_service = InMemorySessionService()

    state = initial_input.copy()
    state.update({
            "problematic_results": problematic_results,
            "original_input": initial_input,
            "feedback": feedback,
    })
    
    # Create a session with initial state
    session = await session_service.create_session(
        app_name="generator",
        user_id="user_id_123",
        session_id="session_id_123",
        state = state,
    )

    # Create empty content since no query is needed
    content = types.Content(role='user', parts=[types.Part(text="")])

    runner = Runner(agent=creator_agent,
                app_name = "generator", 
                session_service=session_service)
    
    # Run the agent
    async for event in runner.run_async(
        user_id="user_id_123", 
        session_id="session_id_123",
        new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print(f"Final Response: {final_response}")
            elif event.actions and event.actions.escalate:
                print(f"Agent escalated: {event.error_message or 'No specific message'}")
        else:
            print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

if __name__ == "__main__":
    asyncio.run(main())