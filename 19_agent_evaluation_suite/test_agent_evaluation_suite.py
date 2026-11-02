import json
import os
from pathlib import Path
from typing import Callable

from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import (
    ArgumentCorrectnessMetric,
    PlanAdherenceMetric,
    PlanQualityMetric,
    StepEfficiencyMetric,
    TaskCompletionMetric,
    ToolCorrectnessMetric,
)
from deepeval.test_case import ToolCall
from deepeval.tracing import (
    observe,
    update_current_span,
    update_current_trace,
)
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MODEL = "gpt-4o-mini"

POLICY_PATH = Path(__file__).parent / "it_support_policy.txt"
RESULTS_PATH = Path(__file__).parent / "agent_evaluation_results.json"

POLICY = POLICY_PATH.read_text(encoding="utf-8")

USER_REQUEST = """
I am employee EMP-204 in Melbourne using macOS. My corporate VPN shows
AUTH-401. I already restarted the VPN client and re-authenticated, but it
still does not connect. Check the service status and create a support ticket
if there is no additional approved fix.
""".strip()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY is missing from the repository-level .env file."
    )

client = OpenAI(api_key=api_key)


# ============================================================
# FICTIONAL TOOL IMPLEMENTATIONS
# ============================================================

@observe(
    type="tool",
    description="Check the corporate VPN service status for a region.",
)
def check_vpn_status(region: str) -> dict:
    return {
        "region": region,
        "service": "Corporate VPN",
        "status": "operational",
        "widespread_outage": False,
    }


@observe(
    type="tool",
    description="Retrieve approved VPN troubleshooting guidance.",
)
def get_vpn_troubleshooting(
    error_code: str,
    operating_system: str,
) -> dict:
    return {
        "error_code": error_code,
        "operating_system": operating_system,
        "approved_steps": [
            "Restart the VPN client",
            "Re-authenticate using the corporate identity provider",
        ],
        "employee_already_completed_steps": True,
        "recommended_action": (
            "Create a P2 VPN support ticket if the issue continues."
        ),
    }


@observe(
    type="tool",
    description="Create a fictional IT support ticket.",
)
def create_support_ticket(
    employee_id: str,
    category: str,
    priority: str,
    summary: str,
) -> dict:
    return {
        "ticket_id": "INC-9001",
        "employee_id": employee_id,
        "category": category,
        "priority": priority,
        "summary": summary,
        "status": "created",
    }


TOOL_FUNCTIONS = {
    "check_vpn_status": check_vpn_status,
    "get_vpn_troubleshooting": get_vpn_troubleshooting,
    "create_support_ticket": create_support_ticket,
}


# ============================================================
# OPENAI TOOL DEFINITIONS
# ============================================================

OPENAI_TOOLS = [
    {
        "type": "function",
        "name": "check_vpn_status",
        "description": (
            "Check whether the corporate VPN is operational in a region."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                },
            },
            "required": ["region"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_vpn_troubleshooting",
        "description": (
            "Retrieve approved troubleshooting guidance for a VPN error."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "error_code": {
                    "type": "string",
                },
                "operating_system": {
                    "type": "string",
                },
            },
            "required": [
                "error_code",
                "operating_system",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "create_support_ticket",
        "description": (
            "Create a fictional support ticket for an unresolved VPN issue."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                },
                "category": {
                    "type": "string",
                },
                "priority": {
                    "type": "string",
                },
                "summary": {
                    "type": "string",
                },
            },
            "required": [
                "employee_id",
                "category",
                "priority",
                "summary",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


# ============================================================
# EXPECTED TOOL TRAJECTORY
# ============================================================

EXPECTED_TOOLS = [
    ToolCall(
        name="check_vpn_status",
        input_parameters={
            "region": "Melbourne",
        },
    ),
    ToolCall(
        name="get_vpn_troubleshooting",
        input_parameters={
            "error_code": "AUTH-401",
            "operating_system": "macOS",
        },
    ),
    ToolCall(
        name="create_support_ticket",
        input_parameters={
            "employee_id": "EMP-204",
            "category": "VPN",
            "priority": "P2",
            "summary": (
                "AUTH-401 VPN failure on macOS; "
                "approved troubleshooting unsuccessful"
            ),
        },
    ),
]

##
FAULTY_TOOLS_CALLED = [
    ToolCall(
        name="check_vpn_status",
        input_parameters={
            "region": "Sydney",
        },
    ),
    ToolCall(
        name="create_support_ticket",
        input_parameters={
            "employee_id": "EMP-204",
            "category": "VPN",
            "priority": "P3",
            "summary": "VPN connection problem",
        },
    ),
]

# ============================================================
# COMPONENT-LEVEL METRICS
# ============================================================

tool_correctness_metric = ToolCorrectnessMetric(
    threshold=0.8,
    should_consider_ordering=True,
)

argument_correctness_metric = ArgumentCorrectnessMetric(
    threshold=0.8,
    model=MODEL,
    include_reason=True,
    async_mode=False,
)


# ============================================================
# AGENT PLANNING
# ============================================================

@observe(
    type="llm",
    model=MODEL,
)
def generate_plan(user_request: str) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=f"""
You are the planning component of an IT support agent.

Create exactly four concise numbered steps.

Requirements:

1. Use the exact tool names in the plan.
2. Do not make extracting user details a separate step.
3. Include both the operational-service and outage branches.
4. Do not claim that a tool has already been called.
5. Do not include explanations outside the four steps.

The plan must follow this structure:

1. Call check_vpn_status for the employee's region.
2. If operational, call get_vpn_troubleshooting for the error code
   and operating system. If there is a widespread outage, do not
   perform individual troubleshooting.
3. If operational and the approved steps have already failed, call
   create_support_ticket once using P2. If there is a widespread
   outage, follow the P1 outage policy.
4. Return the verified service status and real ticket reference,
   without inventing any result.

POLICY:

{POLICY}
""",
        input=user_request,
    )

    plan = response.output_text

    update_current_span(
        input=user_request,
        output=plan,
        metadata={
            "component": "agent_planning",
        },
    )

    return plan


# ============================================================
# INDIVIDUAL AGENT DECISION
# ============================================================

@observe(
    type="llm",
    model=MODEL,
    metrics=[
        tool_correctness_metric,
        argument_correctness_metric,
    ],
)
def make_agent_decision(
    user_request: str,
    plan: str,
    conversation: list,
    instructions: str,
    expected_tool: ToolCall,
    decision_number: int,
    observed_tool_results: list,
):
    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=conversation,
        tools=OPENAI_TOOLS,
        parallel_tool_calls=False,
    )

    function_calls = [
        item
        for item in response.output
        if item.type == "function_call"
    ]

    actual_tool_calls = []

    for function_call in function_calls:
        arguments = json.loads(function_call.arguments)

        actual_tool_calls.append(
            ToolCall(
                name=function_call.name,
                input_parameters=arguments,
            )
        )

    if actual_tool_calls:
        decision_output = (
            f"Decision {decision_number}: "
            f"call {actual_tool_calls[0].name}"
        )
    else:
        decision_output = (
            response.output_text
            or f"Decision {decision_number}: no tool selected"
        )

    if observed_tool_results:
        observed_results_text = json.dumps(
            observed_tool_results,
            indent=2,
        )
    else:
        observed_results_text = (
            "No previous tool results. This is the first decision."
        )

    update_current_span(
        input=(
            f"USER REQUEST:\n{user_request}\n\n"
            f"APPROVED PLAN:\n{plan}\n\n"
            f"OBSERVED TOOL RESULTS:\n{observed_results_text}\n\n"
            f"CURRENT DECISION NUMBER: {decision_number}"
        ),
        output=decision_output,
        tools_called=actual_tool_calls,
        expected_tools=[expected_tool],
        metadata={
            "component": "agent_tool_decision",
            "decision_number": decision_number,
            "observed_tool_results": observed_tool_results,
        },
    )

    return response


# ============================================================
# FINAL RESPONSE GENERATION
# ============================================================

@observe(
    type="llm",
    model=MODEL,
)
def generate_final_response(
    user_request: str,
    plan: str,
    conversation: list,
    observed_tool_results: list,
) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=f"""
You are the final-response component of an IT support agent.

Use only the verified tool results supplied in the conversation.

Requirements:

- State the verified VPN service status.
- State whether the approved troubleshooting was already completed.
- If a support ticket was created, return its real ticket reference.
- Do not invent results, references, response times or promises.
- Do not claim that support will contact the employee shortly.
- Keep the response concise and professional.

POLICY:

{POLICY}
""",
        input=conversation,
    )

    final_output = response.output_text

    update_current_span(
        input=(
            f"USER REQUEST:\n{user_request}\n\n"
            f"APPROVED PLAN:\n{plan}\n\n"
            "VERIFIED TOOL RESULTS:\n"
            f"{json.dumps(observed_tool_results, indent=2)}"
        ),
        output=final_output,
        metadata={
            "component": "final_response",
            "observed_tool_results": observed_tool_results,
        },
    )

    return final_output


# ============================================================
# POSITIVE AGENT EXECUTION
# ============================================================

@observe(
    type="agent",
    available_tools=[
        "check_vpn_status",
        "get_vpn_troubleshooting",
        "create_support_ticket",
    ],
)
def execute_plan(
    user_request: str,
    plan: str,
) -> str:
    conversation = [
        {
            "role": "user",
            "content": (
                f"USER REQUEST:\n{user_request}\n\n"
                f"APPROVED PLAN:\n{plan}"
            ),
        }
    ]

    instructions = f"""
You are the execution component of an IT support agent.

Follow the supplied plan and policy exactly.

For each model call:

- Select only the next required tool.
- Call no more than one tool.
- Follow the order in the approved plan.
- Do not repeat a tool that has already been called.
- Do not invent tool results.
- Use information returned by earlier tools.
- If the VPN has a widespread outage, do not perform individual
  troubleshooting.
- Create a P2 ticket only when the service is operational and the
  employee has already completed the approved troubleshooting.

POLICY:

{POLICY}
"""

    completed_tool_calls = []
    observed_tool_results = []

    for decision_number, expected_tool in enumerate(
        EXPECTED_TOOLS,
        start=1,
    ):
        response = make_agent_decision(
            user_request=user_request,
            plan=plan,
            conversation=conversation,
            instructions=instructions,
            expected_tool=expected_tool,
            decision_number=decision_number,
            observed_tool_results=observed_tool_results,
        )

        conversation.extend(response.output)

        function_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not function_calls:
            premature_output = (
                response.output_text
                or "The agent stopped before completing the approved plan."
            )

            update_current_span(
                input=user_request,
                output=premature_output,
                metadata={
                    "component": "agent_execution",
                    "status": "stopped_before_plan_completion",
                    "completed_tool_calls": completed_tool_calls,
                    "observed_tool_results": observed_tool_results,
                },
            )

            return premature_output

        function_call = function_calls[0]
        tool_name = function_call.name
        arguments = json.loads(function_call.arguments)

        if tool_name not in TOOL_FUNCTIONS:
            tool_result = {
                "error": f"Unknown tool requested: {tool_name}",
            }
        else:
            tool_result = TOOL_FUNCTIONS[tool_name](**arguments)

        completed_tool_calls.append(tool_name)

        observed_tool_results.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "result": tool_result,
            }
        )

        conversation.append(
            {
                "type": "function_call_output",
                "call_id": function_call.call_id,
                "output": json.dumps(tool_result),
            }
        )

    final_output = generate_final_response(
        user_request=user_request,
        plan=plan,
        conversation=conversation,
        observed_tool_results=observed_tool_results,
    )

    update_current_span(
        input=user_request,
        output=final_output,
        metadata={
            "component": "agent_execution",
            "status": "completed",
            "completed_tool_calls": completed_tool_calls,
            "observed_tool_results": observed_tool_results,
        },
    )

    return final_output


# ============================================================
# TOP-LEVEL POSITIVE AGENT
# ============================================================

@observe(
    type="agent",
    available_tools=[
        "check_vpn_status",
        "get_vpn_troubleshooting",
        "create_support_ticket",
    ],
)
def it_support_agent(user_request: str) -> str:
    plan = generate_plan(user_request)

    print("\nAgent Plan")
    print("=" * 70)
    print(plan)

    final_output = execute_plan(
        user_request=user_request,
        plan=plan,
    )

    update_current_trace(
        input=user_request,
        output=final_output,
        expected_tools=EXPECTED_TOOLS,
        metadata={
            "agent": "IT Support Agent",
            "scenario": "Unresolved individual VPN incident",
            "expected_priority": "P2",
        },
    )

    return final_output


# ============================================================
# CONTROLLED FAULTY AGENT
# ============================================================

@observe(
    type="agent",
    available_tools=[
        "check_vpn_status",
        "get_vpn_troubleshooting",
        "create_support_ticket",
    ],
)
def execute_faulty_plan(user_request: str) -> str:
    """
    Controlled negative test.

    Deliberate failures:
    1. Checks Sydney instead of Melbourne.
    2. Skips get_vpn_troubleshooting.
    3. Creates a P3 ticket instead of P2.
    """

    wrong_status_result = check_vpn_status(
        region="Sydney",
    )

    wrong_ticket_result = create_support_ticket(
        employee_id="EMP-204",
        category="VPN",
        priority="P3",
        summary="VPN connection problem",
    )

    faulty_output = (
        "The VPN service was checked in Sydney and is operational. "
        "I skipped the approved troubleshooting check and created a "
        "P3 support ticket.\n\n"
        f"Ticket Reference: {wrong_ticket_result['ticket_id']}"
    )

    update_current_span(
        input=user_request,
        output=faulty_output,
        metadata={
            "component": "faulty_agent_execution",
            "deliberate_failures": [
                "wrong_region",
                "troubleshooting_tool_skipped",
                "wrong_ticket_priority",
            ],
            "tool_results": [
                wrong_status_result,
                wrong_ticket_result,
            ],
        },
    )

    return faulty_output


@observe(
    type="agent",
    available_tools=[
        "check_vpn_status",
        "get_vpn_troubleshooting",
        "create_support_ticket",
    ],
)
def faulty_it_support_agent(user_request: str) -> str:
    final_output = execute_faulty_plan(user_request)

    update_current_trace(
        input=user_request,
        output=final_output,
        tools_called=FAULTY_TOOLS_CALLED,
        expected_tools=EXPECTED_TOOLS,
        metadata={
            "agent": "Controlled Faulty IT Support Agent",
            "scenario": (
                "Wrong region, skipped troubleshooting tool "
                "and wrong ticket priority"
            ),
            "expected_result": "FAIL",
        },
    )

    return final_output


# ============================================================
# TRAJECTORY-LEVEL POSITIVE METRICS
# ============================================================

task_completion_metric = TaskCompletionMetric(
    threshold=0.8,
    task=(
        "Check the Melbourne VPN service status, retrieve the approved "
        "AUTH-401 troubleshooting guidance for macOS and create one P2 "
        "support ticket if the issue remains unresolved. Return the real "
        "ticket reference to the employee."
    ),
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

step_efficiency_metric = StepEfficiencyMetric(
    threshold=0.8,
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

plan_quality_metric = PlanQualityMetric(
    threshold=0.8,
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

plan_adherence_metric = PlanAdherenceMetric(
    threshold=0.8,
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

POSITIVE_TRAJECTORY_METRICS = [
    task_completion_metric,
    step_efficiency_metric,
    plan_quality_metric,
    plan_adherence_metric,
]


# ============================================================
# CONTROLLED-FAILURE METRICS
# ============================================================

failure_task_completion_metric = TaskCompletionMetric(
    threshold=0.8,
    task=(
        "Check the Melbourne VPN service status, retrieve the approved "
        "AUTH-401 troubleshooting guidance for macOS, create one P2 "
        "support ticket and return the real ticket reference."
    ),
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

failure_tool_correctness_metric = ToolCorrectnessMetric(
    threshold=0.8,
    should_consider_ordering=True,
)

failure_argument_correctness_metric = ArgumentCorrectnessMetric(
    threshold=0.8,
    model=MODEL,
    include_reason=True,
    async_mode=False,
)

FAILURE_METRICS = [
    failure_task_completion_metric,
    failure_tool_correctness_metric,
    failure_argument_correctness_metric,
]


# ============================================================
# EVALUATION DATASETS
# ============================================================

positive_dataset = EvaluationDataset(
    goldens=[
        Golden(
            input=USER_REQUEST,
        )
    ]
)

failure_dataset = EvaluationDataset(
    goldens=[
        Golden(
            input=USER_REQUEST,
        )
    ]
)


# ============================================================
# EVALUATION RESULT CAPTURE
# ============================================================

def run_agent_evaluation(
    dataset: EvaluationDataset,
    metrics: list,
    agent_function: Callable[[str], str],
    output_heading: str,
):
    """
    Execute DeepEval's evals_iterator and capture the EvaluationResult
    returned through StopIteration.value.

    A normal for-loop discards this returned EvaluationResult.
    """

    evaluation_iterator = dataset.evals_iterator(
        metrics=metrics,
    )

    while True:
        try:
            golden = next(evaluation_iterator)

        except StopIteration as stop:
            if stop.value is None:
                raise RuntimeError(
                    "DeepEval completed without returning an "
                    "EvaluationResult."
                )

            return stop.value

        actual_output = agent_function(golden.input)

        print(f"\n{output_heading}")
        print("=" * 70)
        print(actual_output)


def serialise_evaluation_result(evaluation_result) -> dict:
    """
    Convert DeepEval's Pydantic EvaluationResult into JSON-safe data.
    """

    if hasattr(evaluation_result, "model_dump"):
        return evaluation_result.model_dump(mode="json")

    if hasattr(evaluation_result, "dict"):
        return evaluation_result.dict()

    raise TypeError(
        "The returned DeepEval EvaluationResult cannot be serialised."
    )


# ============================================================
# RUN POSITIVE EVALUATION
# ============================================================

print("Employee Request")
print("=" * 70)
print(USER_REQUEST)

positive_evaluation_result = run_agent_evaluation(
    dataset=positive_dataset,
    metrics=POSITIVE_TRAJECTORY_METRICS,
    agent_function=it_support_agent,
    output_heading="Agent Final Output",
)


# ============================================================
# RUN CONTROLLED FAILURE
# ============================================================

print("\n\nControlled Failure Scenario")
print("=" * 70)
print(
    "The faulty agent deliberately checks the wrong region, skips the "
    "troubleshooting tool and creates the wrong ticket priority."
)

failure_evaluation_result = run_agent_evaluation(
    dataset=failure_dataset,
    metrics=FAILURE_METRICS,
    agent_function=faulty_it_support_agent,
    output_heading="Faulty Agent Final Output",
)


# ============================================================
# SAVE RESULTS
# ============================================================

all_results = {
    "module": "Agent Behaviour Evaluation Suite",
    "model": MODEL,
    "test_input": USER_REQUEST,
    "expected_tools": [
        {
            "name": tool.name,
            "input_parameters": tool.input_parameters,
        }
        for tool in EXPECTED_TOOLS
    ],
    "positive_test": serialise_evaluation_result(
        positive_evaluation_result
    ),
    "controlled_failure_test": serialise_evaluation_result(
        failure_evaluation_result
    ),
}

with open(
    RESULTS_PATH,
    "w",
    encoding="utf-8",
) as results_file:
    json.dump(
        all_results,
        results_file,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n\nAgent Evaluation Suite Summary")
print("=" * 70)
print("Positive scenario: evaluation completed")
print("Controlled failure: evaluation completed")
print(f"Results saved to: {RESULTS_PATH}")
print(
    "Inspect the latest trace with: "
    "deepeval inspect .deepeval/.latest_run_full.json"
)