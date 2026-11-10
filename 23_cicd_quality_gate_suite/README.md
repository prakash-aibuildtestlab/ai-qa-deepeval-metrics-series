# AI Evaluation CI/CD Quality Gate

This module demonstrates how to run AI evaluation tests automatically in
GitHub Actions and block a release when required AI behaviours regress.

It builds on:

- `22_evaluation_automation_suite`
- Pytest markers
- Approved evaluation baselines
- Deterministic policy checks
- Machine-readable JSON reports
- Process exit codes

## Objective

A high overall pass rate should not automatically approve an AI release.

For example, seven passing tests must not compensate for one critical privacy
or verification failure.

This module converts evaluation results into an automated CI/CD decision:

- `PASS` allows the pipeline to continue.
- `BLOCK` fails the pipeline.
- Missing evidence also blocks the pipeline.

## Architecture

```text
Pull request or push
        |
        v
GitHub Actions workflow
        |
        v
Install Python dependencies
        |
        v
Test the quality-gate logic
        |
        v
Run smoke evaluations
        |
        v
Run critical evaluations
        |
        v
Run safety evaluations
        |
        v
Run regression evaluations
        |
        v
Generate CI summary
        |
        v
Apply release gate
        |
        +---- PASS ----> Exit code 0
        |
        +---- BLOCK ---> Exit code 1


Test Suites
Suite	Purpose	Executions	Required pass rate	Blocking
Smoke	Essential behaviour on every change	4	100%	Yes
Critical	Verification and business-critical rules	4	100%	Yes
Safety	Privacy, role and unsupported-action checks	4	100%	Yes
Regression	Compare current behaviour with the approved baseline	8	100%	Yes


The test cases overlap across suites. Therefore, the pipeline runs 20 test
executions across eight unique evaluation scenarios.
Files
23_cicd_quality_gate_suite/
├── README.md
├── HOW_TO_RUN.txt
├── requirements.txt
├── quality_gate_config.json
├── generate_ci_summary.py
├── test_ci_quality_gate.py
└── reports/
    ├── smoke_results.json
    ├── critical_results.json
    ├── safety_results.json
    ├── regression_results.json
    ├── ci_quality_gate_summary.json
    └── github_step_summary.md

The GitHub Actions workflow is stored at the repository root:
.github/workflows/ai-evaluation-quality-gate.yml

GitHub only detects workflow files stored under .github/workflows.
Quality-Gate Rules
The release is blocked when:
- A required report is missing.
- No tests were executed for a blocking stage.
- A selected evaluation test fails.
- Pytest reports a collection or execution error.
- A stage pass rate is below its configured threshold.
- A critical, safety or regression expectation fails.
All four stages currently require a 100% pass rate.

This is intentional. The portfolio scenario contains release-critical policy,
privacy and verification behaviours that must not be averaged away.
Fail-Closed Behaviour
The gate follows a fail-closed design.

If critical test evidence is missing, the system does not assume success.
Instead, it produces:
Release gate: BLOCK
Exit code: 1

This behaviour was verified locally by temporarily running the summary without
the critical report. The gate correctly blocked the release.
Local Passing Result
The complete local run produced:
SMOKE       Tests: 4   Passed: 4   Failed: 0   Result: PASS
CRITICAL    Tests: 4   Passed: 4   Failed: 0   Result: PASS
SAFETY      Tests: 4   Passed: 4   Failed: 0   Result: PASS
REGRESSION  Tests: 8   Passed: 8   Failed: 0   Result: PASS

Total executions: 20
Release gate: PASS
Exit code: 0

GitHub Actions Behaviour
The workflow runs when:
- A pull request changes Module 22, Module 23 or the workflow.
- A change is pushed to main.
- A user starts it manually through workflow_dispatch.
Each test stage uses continue-on-error: true so the workflow can finish all
evaluation stages and preserve complete evidence.

This does not approve failed tests.

The final summary script evaluates all stage reports and returns the real
pipeline decision.
Reports and Evidence
The pipeline produces:
- One pytest JSON report per evaluation stage.
- A consolidated quality-gate JSON summary.
- A Markdown summary displayed in the GitHub Actions run.
- A downloadable GitHub Actions artifact containing all reports.
Artifacts are retained for 14 days.
Exit Codes
Exit code	Meaning
0	All blocking evaluation stages passed
1	Release blocked by an evaluation failure
2	Quality-gate configuration error


These exit codes allow the same evaluation gate to be used in GitHub Actions,
GitLab CI, Jenkins, Azure DevOps or another CI/CD platform.
API Key Requirements
The current CI gate runs deterministic tests against approved stored outputs.

Therefore:
OPENAI_API_KEY is not required

In a production implementation, expensive or non-deterministic LLM-judge tests
would normally run separately, for example:
- On a schedule
- Before a release
- After a prompt or model change
- Through a manually approved workflow
Fast deterministic checks should remain in the pull-request gate.
Real-World Testing Principle
A test score is not the release decision.

The release decision should also consider:
- Failure severity
- Policy impact
- Privacy impact
- Missing evaluation evidence
- Test errors
- Regression against an approved baseline
The most important rule demonstrated by this module is:
One critical AI regression can outweigh several passing evaluation tests.