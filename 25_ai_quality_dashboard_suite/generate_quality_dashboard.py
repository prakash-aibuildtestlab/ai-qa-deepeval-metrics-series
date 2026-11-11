import argparse
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(file_path):
    with Path(file_path).open(encoding="utf-8") as file:
        return json.load(file)


def write_json(file_path, payload):
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def create_check(
    check_id,
    category,
    description,
    actual,
    expected,
    passed,
    severity,
    release_blocking,
):
    return {
        "check_id": check_id,
        "category": category,
        "description": description,
        "actual": actual,
        "expected": expected,
        "passed": passed,
        "result": "PASS" if passed else "FAIL",
        "severity": severity,
        "release_blocking": release_blocking,
    }


def build_quality_checks(
    config,
    pre_release,
    cicd,
    production,
    human_review,
):
    thresholds = config["quality_thresholds"]
    blocking_rules = config["release_blocking_rules"]

    production_operations = production[
        "operational_metrics"
    ]
    production_safety = production["safety_metrics"]
    production_semantic = production["semantic_metrics"]
    production_alerts = production["alerts"]

    checks = [
        create_check(
            check_id="CHECK-001",
            category="pre_release",
            description="Pre-release evaluation pass rate",
            actual=pre_release["pass_rate"],
            expected=(
                f">= "
                f"{thresholds['minimum_pre_release_pass_rate']}"
            ),
            passed=(
                pre_release["pass_rate"]
                >= thresholds[
                    "minimum_pre_release_pass_rate"
                ]
            ),
            severity="high",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-002",
            category="pre_release",
            description="Critical pre-release failures",
            actual=pre_release["critical_failures"],
            expected="0",
            passed=pre_release["critical_failures"] == 0,
            severity="critical",
            release_blocking=blocking_rules[
                "block_on_failed_critical_test"
            ],
        ),
        create_check(
            check_id="CHECK-003",
            category="cicd",
            description="CI/CD test pass rate",
            actual=cicd["pass_rate"],
            expected=(
                f">= "
                f"{thresholds['minimum_cicd_pass_rate']}"
            ),
            passed=(
                cicd["pass_rate"]
                >= thresholds["minimum_cicd_pass_rate"]
            ),
            severity="high",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-004",
            category="cicd",
            description="CI/CD release gate",
            actual=cicd["release_gate"],
            expected="PASS",
            passed=cicd["release_gate"] == "PASS",
            severity="critical",
            release_blocking=blocking_rules[
                "block_on_cicd_gate_failure"
            ],
        ),
        create_check(
            check_id="CHECK-005",
            category="production",
            description="Production semantic pass rate",
            actual=production_semantic[
                "semantic_pass_rate"
            ],
            expected=(
                f">= "
                f"{thresholds['minimum_production_semantic_pass_rate']}"
            ),
            passed=(
                production_semantic["semantic_pass_rate"]
                >= thresholds[
                    "minimum_production_semantic_pass_rate"
                ]
            ),
            severity="high",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-006",
            category="production",
            description="Production error rate",
            actual=production_operations["error_rate"],
            expected=(
                f"<= "
                f"{thresholds['maximum_production_error_rate']}"
            ),
            passed=(
                production_operations["error_rate"]
                <= thresholds[
                    "maximum_production_error_rate"
                ]
            ),
            severity="high",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-007",
            category="production",
            description="Negative feedback rate",
            actual=production_operations[
                "negative_feedback_rate"
            ],
            expected=(
                f"<= "
                f"{thresholds['maximum_negative_feedback_rate']}"
            ),
            passed=(
                production_operations[
                    "negative_feedback_rate"
                ]
                <= thresholds[
                    "maximum_negative_feedback_rate"
                ]
            ),
            severity="medium",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-008",
            category="production",
            description="Production P95 latency",
            actual=production_operations[
                "p95_latency_ms"
            ],
            expected=(
                f"<= "
                f"{thresholds['maximum_p95_latency_ms']} ms"
            ),
            passed=(
                production_operations["p95_latency_ms"]
                <= thresholds[
                    "maximum_p95_latency_ms"
                ]
            ),
            severity="medium",
            release_blocking=False,
        ),
        create_check(
            check_id="CHECK-009",
            category="production",
            description="Unresolved critical alerts",
            actual=production_alerts["critical"],
            expected=(
                f"<= "
                f"{thresholds['maximum_unresolved_critical_alerts']}"
            ),
            passed=(
                production_alerts["critical"]
                <= thresholds[
                    "maximum_unresolved_critical_alerts"
                ]
            ),
            severity="critical",
            release_blocking=blocking_rules[
                "block_on_unresolved_critical_alert"
            ],
        ),
        create_check(
            check_id="CHECK-010",
            category="safety",
            description="Production PII incidents",
            actual=production_safety["pii_incidents"],
            expected="0",
            passed=production_safety["pii_incidents"] == 0,
            severity="critical",
            release_blocking=blocking_rules[
                "block_on_privacy_incident"
            ],
        ),
        create_check(
            check_id="CHECK-011",
            category="safety",
            description="Unsupported action claims",
            actual=production_safety[
                "unsupported_action_claims"
            ],
            expected="0",
            passed=(
                production_safety[
                    "unsupported_action_claims"
                ]
                == 0
            ),
            severity="critical",
            release_blocking=blocking_rules[
                "block_on_unsupported_action_claim"
            ],
        ),
        create_check(
            check_id="CHECK-012",
            category="human_review",
            description="Pending human reviews",
            actual=human_review["pending_reviews"],
            expected=(
                f"<= "
                f"{thresholds['maximum_pending_human_reviews']}"
            ),
            passed=(
                human_review["pending_reviews"]
                <= thresholds[
                    "maximum_pending_human_reviews"
                ]
            ),
            severity="high",
            release_blocking=False,
        ),
    ]

    return checks


def calculate_quality_score(checks):
    total_weight = 0
    passed_weight = 0

    for check in checks:
        weight = 2 if check["release_blocking"] else 1
        total_weight += weight

        if check["passed"]:
            passed_weight += weight

    if total_weight == 0:
        return 0.0

    return round(
        (passed_weight / total_weight) * 100,
        2,
    )


def determine_decision(checks):
    blocking_failures = [
        check
        for check in checks
        if (
            not check["passed"]
            and check["release_blocking"]
        )
    ]

    non_blocking_failures = [
        check
        for check in checks
        if (
            not check["passed"]
            and not check["release_blocking"]
        )
    ]

    if blocking_failures:
        return "BLOCK"

    if non_blocking_failures:
        return "CONDITIONAL"

    return "APPROVE"


def build_recommendations(checks):
    recommendations = []

    failed_check_ids = {
        check["check_id"]
        for check in checks
        if not check["passed"]
    }

    if "CHECK-009" in failed_check_ids:
        recommendations.append(
            "Resolve all critical production alerts before "
            "approving another release."
        )

    if "CHECK-010" in failed_check_ids:
        recommendations.append(
            "Investigate the PII incident, confirm containment "
            "and complete privacy remediation."
        )

    if "CHECK-011" in failed_check_ids:
        recommendations.append(
            "Correct unsupported action claims and add the "
            "confirmed incident to regression coverage."
        )

    if "CHECK-005" in failed_check_ids:
        recommendations.append(
            "Review failed semantic evaluations and recalibrate "
            "the applicable evaluators."
        )

    if {
        "CHECK-006",
        "CHECK-008",
    }.intersection(failed_check_ids):
        recommendations.append(
            "Investigate production reliability and latency "
            "before increasing traffic."
        )

    if "CHECK-007" in failed_check_ids:
        recommendations.append(
            "Analyse negative feedback themes and prioritise "
            "the highest-impact customer issues."
        )

    return recommendations


def build_category_summary(checks):
    categories = {}

    for check in checks:
        category = check["category"]

        if category not in categories:
            categories[category] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "result": "PASS",
            }

        categories[category]["total"] += 1

        if check["passed"]:
            categories[category]["passed"] += 1
        else:
            categories[category]["failed"] += 1
            categories[category]["result"] = "FAIL"

    return categories


def build_quality_summary(
    config,
    pre_release,
    cicd,
    production,
    human_review,
    regression_feedback,
):
    checks = build_quality_checks(
        config=config,
        pre_release=pre_release,
        cicd=cicd,
        production=production,
        human_review=human_review,
    )

    failed_checks = [
        check
        for check in checks
        if not check["passed"]
    ]

    blocking_failures = [
        check
        for check in failed_checks
        if check["release_blocking"]
    ]

    decision = determine_decision(checks)

    return {
        "dashboard_name": config["dashboard_name"],
        "dashboard_version": config[
            "dashboard_version"
        ],
        "system_name": config["system_name"],
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "overall_decision": decision,
        "quality_score": calculate_quality_score(checks),
        "decision_summary": {
            "APPROVE": (
                "All configured quality gates passed."
            ),
            "CONDITIONAL": (
                "No blocking risk exists, but one or more "
                "non-critical thresholds require action."
            ),
            "BLOCK": (
                "One or more release-blocking quality risks "
                "remain unresolved."
            ),
        }[decision],
        "check_summary": {
            "total": len(checks),
            "passed": len(checks) - len(failed_checks),
            "failed": len(failed_checks),
            "blocking_failures": len(blocking_failures),
        },
        "category_summary": build_category_summary(
            checks
        ),
        "quality_checks": checks,
        "blocking_reasons": [
            {
                "check_id": check["check_id"],
                "description": check["description"],
                "actual": check["actual"],
                "expected": check["expected"],
            }
            for check in blocking_failures
        ],
        "recommendations": build_recommendations(checks),
        "lifecycle_summary": {
            "pre_release_status": pre_release[
                "quality_status"
            ],
            "cicd_release_gate": cicd["release_gate"],
            "production_status": production[
                "monitoring_status"
            ],
            "human_review_status": human_review[
                "review_status"
            ],
            "regression_cases_created": (
                regression_feedback[
                    "total_regression_cases"
                ]
            ),
        },
        "source_results": {
            "pre_release": pre_release,
            "cicd": cicd,
            "production": production,
            "human_review": human_review,
            "regression_feedback": regression_feedback,
        },
    }


def render_html_dashboard(summary, output_path):
    environment = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(
            enabled_extensions=("html",)
        ),
    )

    template = environment.get_template(
        "dashboard.html"
    )

    html = template.render(summary=summary)

    html = "\n".join(
        line.rstrip()
        for line in html.splitlines()
    ) + "\n"

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        html,
        encoding="utf-8",
    )





def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Generate the AI quality governance summary."
        )
    )

    parser.add_argument(
        "--config",
        default="dashboard_config.json",
        help="Path to the dashboard configuration.",
    )

    parser.add_argument(
        "--enforce-gate",
        action="store_true",
        help=(
            "Return exit code 1 when the overall "
            "quality decision is BLOCK."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    config_path = ROOT / args.config
    config = load_json(config_path)

    sources = config["data_sources"]

    pre_release = load_json(
        ROOT / sources["pre_release"]
    )
    cicd = load_json(ROOT / sources["cicd"])
    production = load_json(
        ROOT / sources["production"]
    )
    human_review = load_json(
        ROOT / sources["human_review"]
    )
    regression_feedback = load_json(
        ROOT / sources["regression_feedback"]
    )

    summary = build_quality_summary(
        config=config,
        pre_release=pre_release,
        cicd=cicd,
        production=production,
        human_review=human_review,
        regression_feedback=regression_feedback,
    )

    output_path = ROOT / config["outputs"]["json_summary"]
    write_json(output_path, summary)
    html_output_path = (
    ROOT / config["outputs"]["html_dashboard"]
)

    render_html_dashboard(
    summary,
    html_output_path,
)

    check_summary = summary["check_summary"]

    print("AI Quality Governance Summary")
    print("=" * 70)
    print(
        "System:",
        summary["system_name"],
    )
    print(
        "Overall decision:",
        summary["overall_decision"],
    )
    print(
        "Quality score:",
        f"{summary['quality_score']:.2f}%",
    )
    print(
        "Checks:",
        (
            f"{check_summary['passed']} passed, "
            f"{check_summary['failed']} failed"
        ),
    )
    print(
        "Blocking failures:",
        check_summary["blocking_failures"],
    )
    print(
        "Regression cases created:",
        summary["lifecycle_summary"][
            "regression_cases_created"
        ],
    )

    if summary["blocking_reasons"]:
        print()
        print("Blocking reasons:")

        for reason in summary["blocking_reasons"]:
            print(
                f"- {reason['check_id']}: "
                f"{reason['description']} "
                f"(actual={reason['actual']}, "
                f"expected={reason['expected']})"
            )

    print()
    print(f"Summary saved to: {output_path}")
    print(f"Dashboard saved to: {html_output_path}")
    if args.enforce_gate:
        if summary["overall_decision"] == "BLOCK":
            print()
            print(
                "Quality gate enforcement: BLOCK "
                "returned exit code 1."
            )
            return 1

        print()
        print("Quality gate enforcement: PASS")
        return 0

    print()
    print(
        "Quality gate enforcement: "
        "NOT REQUESTED (reporting mode)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())