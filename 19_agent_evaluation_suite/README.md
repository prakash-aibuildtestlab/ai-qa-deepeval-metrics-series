# Agent Behaviour Evaluation Suite

This module demonstrates how to test the behaviour of a tool-using AI agent with DeepEval.

Unlike a normal chatbot evaluation, agent testing must examine both:

1. The final answer produced by the agent.
2. The internal trajectory used to complete the task.

The suite evaluates planning, tool selection, tool arguments, task completion and execution efficiency.

---

## Scenario

The application is a fictional corporate IT support agent.

An employee reports:

- Employee ID: `EMP-204`
- Region: Melbourne
- Operating system: macOS
- VPN error: `AUTH-401`
- The employee already restarted and re-authenticated
- The VPN still does not connect

The agent must:

1. Check the Melbourne VPN service status.
2. Retrieve approved troubleshooting guidance.
3. Confirm that the approved troubleshooting has already failed.
4. Create one P2 support ticket.
5. Return the real ticket reference.

---

## Available tools

### `check_vpn_status`

Checks whether the corporate VPN service is operational in a region.

Expected argument:

```json
{
  "region": "Melbourne"
}

get_vpn_troubleshooting
Retrieves approved troubleshooting guidance for a VPN error.

Expected arguments:
{
  "error_code": "AUTH-401",
  "operating_system": "macOS"
}

create_support_ticket
Creates a fictional IT support ticket.

Expected arguments:
{
  "employee_id": "EMP-204",
  "category": "VPN",
  "priority": "P2",
  "summary": "AUTH-401 VPN failure on macOS; approved troubleshooting unsuccessful"
}

Agent trace
DeepEval's @observe decorator captures the complete agent trajectory.
IT Support Agent
├── Generate plan
└── Execute plan
    ├── Make tool decision
    ├── Check VPN status
    ├── Make tool decision
    ├── Get VPN troubleshooting
    ├── Make tool decision
    ├── Create support ticket
    └── Generate final response

Each tool-decision span contains:
- The user request
- The approved plan
- Previous tool observations
- The expected tool
- The actual tool
- Actual tool arguments
Metrics evaluated
Metric	Purpose
Task Completion	Did the agent complete the employee's requested goal?
Tool Correctness	Did the agent select the correct tools in the correct order?
Argument Correctness	Did it pass the correct values to each tool?
Step Efficiency	Did it complete the task without unnecessary steps?
Plan Quality	Was the generated plan complete and appropriate?
Plan Adherence	Did the execution follow the generated plan?


Positive test
The correct agent:
- Checked the Melbourne VPN service
- Used AUTH-401 and macOS
- Retrieved the approved troubleshooting guidance
- Created a P2 ticket
- Returned ticket reference INC-9001
Results
Metric	Score	Threshold	Result
Task Completion	0.95	0.80	PASS
Tool Correctness	1.00	0.80	PASS
Argument Correctness	1.00	0.80	PASS
Step Efficiency	0.50	0.80	FAIL
Plan Quality	0.50	0.80	FAIL
Plan Adherence	0.00	0.80	FAIL


The agent completed the business goal and used the expected tools and arguments.

However, the planning metrics penalised the additional LLM decision spans used by the agent architecture.
Controlled failure test
The faulty agent deliberately:
- Checked Sydney instead of Melbourne
- Skipped get_vpn_troubleshooting
- Created a P3 ticket instead of P2
Results
Metric	Score	Threshold	Result
Task Completion	0.30	0.80	FAIL
Tool Correctness	0.67	0.80	FAIL
Argument Correctness	0.50	0.80	FAIL


The controlled negative test confirms that the evaluation suite can detect:
- Wrong tool arguments
- Missing tools
- Incorrect tool order
- Incorrect business decisions
- Incomplete task execution
Important evaluation lesson
The positive agent completed the task correctly, but some planning metrics still failed.

For example:
- The Plan Quality reason claimed that service-status and outage handling were missing, although both were present in the plan.
- Plan Adherence treated the intermediate LLM decision spans as unnecessary actions, even though they were part of the agent implementation.
- Step Efficiency considered the planning and decision calls excessive for a relatively simple workflow.
This demonstrates an important AI QA principle:
A metric score is evidence, not unquestionable truth.

Always inspect:
- The execution trace
- The metric reason
- The actual tool calls
- The tool arguments
- The test-case design
- Whether the metric evaluated the intended trace level
Project files
19_agent_evaluation_suite/
├── README.md
├── HOW_TO_RUN.txt
├── requirements.txt
├── it_support_policy.txt
├── test_agent_evaluation_suite.py
└── agent_evaluation_results.json

Setup
From the repository root:
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 19_agent_evaluation_suite/requirements.txt

Create a repository-level .env file:
OPENAI_API_KEY=your_openai_api_key_here

Do not commit the real .env file.
Run the suite
cd 19_agent_evaluation_suite
python -m py_compile test_agent_evaluation_suite.py
python test_agent_evaluation_suite.py

The script performs:
1. A live positive agent evaluation.
2. A controlled faulty-agent evaluation.
3. JSON result export.
Results are saved to:
agent_evaluation_results.json

Inspect the trace
DeepEval automatically stores the latest local trace.
deepeval inspect .deepeval/.latest_run_full.json

Because the controlled failure runs last, .latest_run_full.json represents the negative run.

The custom agent_evaluation_results.json file preserves both positive and negative evaluation results.
Technology
- Python
- OpenAI API
- DeepEval
- DeepEval tracing
- LLM tool calling
- LLM-as-a-judge metrics
Key takeaway
Testing an agent requires more than checking its final answer.

A reliable agent evaluation should verify:
- What goal was completed
- Which tools were selected
- The order of tool calls
- The arguments passed to tools
- The quality of the plan
- Whether execution followed the plan
- Whether unnecessary steps were introduced
- How the agent behaves when something goes wrong

Then run:

```bash
python -m json.tool agent_evaluation_results.json > /dev/null \
  && echo "Results JSON is valid"

git add README.md
git add test_agent_evaluation_suite.py
git add it_support_policy.txt
git add agent_evaluation_results.json

git status --short
git diff --cached --check
git diff --cached --name-only

Expected staged files:
19_agent_evaluation_suite/README.md
19_agent_evaluation_suite/agent_evaluation_results.json
19_agent_evaluation_suite/it_support_policy.txt
19_agent_evaluation_suite/test_agent_evaluation_suite.py