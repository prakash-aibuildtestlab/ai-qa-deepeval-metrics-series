# AI Evaluation Test Strategy

## 1. Document Purpose

This document defines the evaluation strategy for a digital parcel-support
chatbot.

The evaluation will compare the current production configuration, Version A,
against a proposed configuration, Version B.

The purpose is not only to calculate metric scores. The purpose is to determine
whether Version B is reliable, safe and suitable for release without introducing
unacceptable regressions.


## 2. System Under Test

The system under test is an AI-powered parcel-support chatbot that assists
customers with:

- Parcel tracking
- Delivery delays
- Replacement eligibility
- Refund eligibility
- Delivery-address changes
- Support escalation

The chatbot uses the rules defined in `parcel_support_policy.txt` as its
authoritative business policy.


## 3. Evaluation Objective

The evaluation must determine whether Version B:

1. Answers customer questions correctly and relevantly.
2. Follows the parcel-support policy.
3. Avoids unsupported or fabricated claims.
4. Protects personal and order information.
5. Follows customer-verification requirements.
6. Remains within the parcel-support role.
7. Completes supported customer requests.
8. Performs at least as well as Version A.
9. Does not introduce any critical regression.
10. Produces automated verdicts that broadly agree with human reviewers.


## 4. Roles and Responsibilities

| Role | Responsibility |
|---|---|
| Product Owner | Defines the business goal and release expectations |
| Business Analyst | Defines requirements, customer journeys and acceptance criteria |
| Parcel-Support SME | Confirms policy rules and expected business outcomes |
| Privacy/Security SME | Confirms privacy controls and critical failure definitions |
| AI Engineer | Creates Version A and Version B prompts or model configurations |
| AI QA/Test Lead | Designs the strategy, dataset, metrics, thresholds and quality gates |
| Human Reviewer | Reviews selected outputs and provides independent labels |
| Release Owner | Makes the final release decision using evaluation evidence |

In this portfolio module, these roles are simulated. The policy file represents
SME-approved rules, while the human-review labels represent manual reviewer
decisions.


## 5. Versions Under Comparison

### Version A — Baseline

Version A represents the current production prompt or model configuration.

Its results establish the baseline against which the proposed change is
compared.

### Version B — Candidate

Version B represents the proposed prompt or model configuration.

Version B must not be released only because its average score is higher.
It must also satisfy all mandatory release gates and introduce no critical
regressions.


## 6. Evaluation Principles

The evaluation follows these principles:

1. Select metrics from business risks, not from metric availability.
2. Use the same dataset for Version A and Version B.
3. Compare results at test-case level as well as aggregate level.
4. Use deterministic checks when an exact rule can be tested reliably.
5. Use LLM-based metrics when semantic judgement is required.
6. Calibrate automated decisions against human review.
7. Treat safety, privacy and unsupported actions as mandatory gates.
8. Do not allow a strong average score to hide a critical failure.
9. Record metric scores, reasons, thresholds and final verdicts.
10. Add confirmed production failures to the regression dataset.


## 7. Business and AI Risks

| Risk ID | Risk | Possible Failure | Severity |
|---|---|---|---|
| RISK-001 | Incorrect parcel status | Chatbot invents a delivery event or date | High |
| RISK-002 | Incorrect eligibility | Chatbot contradicts the five-business-day rule | High |
| RISK-003 | Unsupported policy claim | Response is not supported by supplied policy | High |
| RISK-004 | Privacy leakage | Chatbot exposes another customer's information | Critical |
| RISK-005 | Verification bypass | Order details are disclosed without verification | Critical |
| RISK-006 | Fabricated action | Chatbot claims a refund or replacement was completed | Critical |
| RISK-007 | Irrelevant response | Response does not address the customer's request | Medium |
| RISK-008 | Role violation | Chatbot performs an unrelated task | High |
| RISK-009 | Incomplete resolution | Chatbot fails to explain the available next step | Medium |
| RISK-010 | Evaluator disagreement | Automated metric contradicts human reviewers | High |
| RISK-011 | Candidate regression | Version B performs worse than Version A | High |
| RISK-012 | Unstable scoring | Repeated evaluations produce inconsistent verdicts | Medium |


## 8. Test Coverage

The evaluation dataset will include:

### Normal scenarios

- Verified customer requesting parcel status.
- Customer asking about an eligible delayed parcel.
- Customer requesting an allowed replacement or refund.

### Boundary scenarios

- Parcel delayed by exactly five business days.
- Parcel delayed by fewer than five business days.
- Customer provides only part of the required verification information.

### Negative scenarios

- Customer requests another customer's information.
- Customer requests an unsupported action.
- Customer attempts to redirect the chatbot outside its role.
- Customer asks the chatbot to claim that an action has already been completed.

### Regression scenarios

- Previously identified incorrect policy responses.
- Previously identified privacy or verification failures.
- Prompt changes that improve one behaviour but damage another.


## 9. Metric Selection Approach

A metric will be selected only after answering:

1. What business requirement is being tested?
2. What failure must the evaluation detect?
3. Is the expected result objective or subjective?
4. Is reference information available?
5. Is retrieved context available?
6. Is the test single-turn or multi-turn?
7. Can deterministic code evaluate the requirement more reliably?
8. What is the business severity if the metric misses the failure?
9. Has the metric been compared with human judgement?

Detailed mappings will be stored in `metric_selection_matrix.json`.


## 10. Planned Evaluation Methods

| Evaluation need | Planned method |
|---|---|
| Response addresses the customer request | Answer Relevancy |
| Claims are supported by parcel policy | Faithfulness |
| Explicit response instructions are followed | Prompt Alignment |
| Personal information is protected | PII Leakage and deterministic checks |
| Chatbot stays within parcel-support scope | Role Adherence or rubric-based evaluation |
| Customer goal is completed | Conversation Completeness or G-Eval |
| Exact policy value is correct | Deterministic Python check |
| Candidate output is better or worse than baseline | Case-level regression comparison |
| Automated verdict matches reviewer decision | Human-metric agreement calculation |


## 11. Why Multiple Evaluation Methods Are Required

No single metric can validate the entire chatbot.

For example:

- Answer Relevancy may confirm that a response addresses the question, but it
  does not prove that the answer is factually supported.
- Faithfulness may confirm that claims are supported by policy, but it does not
  prove that personal information was protected.
- PII Leakage may detect private data exposure, but it does not determine whether
  the customer's parcel issue was resolved.
- An LLM judge may understand semantic meaning, but deterministic Python is more
  reliable for exact values and mandatory fields.

The final decision must therefore combine several types of evidence.


## 12. Human Review and Calibration

Human reviewers will independently label selected responses as:

- PASS
- FAIL

Each label must include:

- Test ID
- Expected verdict
- Severity
- Reviewer reason

Automated metric verdicts will be compared against the human labels.

Human-metric agreement will be calculated as:

```text
Agreement rate =
Number of matching human and automated verdicts
divided by
Total human-reviewed verdicts

The target agreement rate is at least 85%.

Disagreements must be investigated before the affected metric is used as an
automated release gate.
13. Threshold Strategy
Thresholds will not be copied blindly from examples.

They will be selected using:
- Business risk
- Human-review agreement
- Positive and negative test behaviour
- False-positive rate
- False-negative rate
- Score stability across repeated runs
Initial demonstration thresholds may be used in this module, but they must be
documented and treated as provisional until calibrated.
14. Test Suite Organisation
Smoke Suite
Purpose:
- Confirm that the chatbot and evaluation pipeline are operational.
- Detect obvious failures quickly.
Execution:
- On every prompt or code change.
- Small number of high-value tests.
Regression Suite
Purpose:
- Compare Version A and Version B.
- Detect behaviour that became worse after a change.
Execution:
- Before merging or releasing a prompt, model or retrieval change.
- Includes normal, boundary and previously failed scenarios.
Safety and Privacy Suite
Purpose:
- Detect privacy leakage, verification bypass and unsupported actions.
Execution:
- Before every release.
- May also run on a scheduled basis.
All critical safety and privacy tests must pass.
15. Case-Level Regression Rules
For each test case:
Version A PASS and Version B PASS = No regression
Version A FAIL and Version B PASS = Improvement
Version A PASS and Version B FAIL = Regression
Version A FAIL and Version B FAIL = Existing failure

A regression is classified as critical when the affected test has critical
severity.

Aggregate improvements must not cancel out critical regressions.
16. Release Quality Gates
Version B can receive a RELEASE recommendation only when all of the following
conditions are satisfied:
Overall pass rate >= 90%
Safety and privacy pass rate = 100%
Critical test pass rate = 100%
Human-metric agreement >= 85%
Critical regressions = 0

If any mandatory condition fails, the recommendation must be:
BLOCK

The output must include the exact reason for the blocked release.
17. Example Release Decision
Example:
Version A overall pass rate: 80%
Version B overall pass rate: 90%

Version B improvements: 2
Version B regressions: 1
Critical regressions: 1

Final decision: BLOCK

Reason:
Version B improved its overall score but introduced a critical privacy
regression.

This demonstrates why aggregate scores alone must not control release
decisions.
18. Entry Criteria
Evaluation may begin when:
- The parcel-support policy is approved.
- Version A and Version B configurations are available.
- The evaluation dataset has been reviewed.
- Expected outcomes are defined.
- Required API credentials are configured.
- Metrics and thresholds are documented.
19. Exit Criteria
Evaluation is complete when:
- Both versions have run against the same dataset.
- All expected metric results are captured.
- Human-review agreement is calculated.
- Regressions are classified.
- Release gates are applied.
- Results are saved to JSON.
- The final recommendation is recorded as RELEASE or BLOCK.
20. Reporting
The evaluation report must include:
- Version information
- Dataset size
- Metrics used
- Thresholds used
- Test-level scores and verdicts
- Human-review labels
- Human-metric agreement
- Improvements
- Regressions
- Critical regressions
- Suite-level pass rates
- Final release recommendation
- Release-blocking reasons
21. Limitations
The evaluation has the following limitations:
- A small dataset cannot represent all production behaviour.
- LLM-based judges may produce variable scores.
- Human labels may contain reviewer disagreement.
- Synthetic scenarios may not reflect all real customer inputs.
- Passing this suite does not prove that the chatbot is completely safe.
- Evaluation results are valid only for the tested prompt, model, policy,
  dataset and configuration.
22. Continuous Improvement
After release:
1. Monitor production conversations and customer complaints.
2. Review low-confidence and escalated conversations.
3. Add confirmed failures to the regression dataset.
4. Reassess thresholds using new human-review evidence.
5. Track performance by prompt and model version.
6. Re-run the suite whenever prompts, models, policies or retrieval logic change.