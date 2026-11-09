import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT = (
    MODULE_DIR
    / "reports"
    / "regression_report.json"
)

DEFAULT_OUTPUT = (
    MODULE_DIR
    / "reports"
    / "evaluation_summary.json"
)


def load_json(file_path: Path) -> dict[str, Any]:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def build_summary(
    pytest_report: dict[str, Any],
    source_file: Path,
) -> dict[str, Any]:
    pytest_summary = pytest_report.get("summary", {})
    tests = pytest_report.get("tests", [])

    total = int(pytest_summary.get("total", len(tests)))
    passed = int(pytest_summary.get("passed", 0))
    failed = int(pytest_summary.get("failed", 0))
    errors = int(pytest_summary.get("error", 0))
    skipped = int(pytest_summary.get("skipped", 0))

    pass_rate = (
        round((passed / total) * 100, 2)
        if total
        else 0.0
    )

    release_gate = (
        "PASS"
        if total > 0 and failed == 0 and errors == 0
        else "BLOCK"
    )

    failed_tests = [
        {
            "node_id": test.get("nodeid"),
            "outcome": test.get("outcome"),
            "duration_seconds": round(
                float(test.get("duration", 0)),
                4,
            ),
        }
        for test in tests
        if test.get("outcome") in {"failed", "error"}
    ]

    test_results = [
        {
            "node_id": test.get("nodeid"),
            "outcome": test.get("outcome"),
            "duration_seconds": round(
                float(test.get("duration", 0)),
                4,
            ),
        }
        for test in tests
    ]

    return {
        "report_name": "AI Evaluation Automation Summary",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_report": source_file.name,
        "framework": "pytest",
        "suite": "regression",
        "results": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate_percent": pass_rate,
            "duration_seconds": round(
                float(pytest_report.get("duration", 0)),
                4,
            ),
        },
        "release_gate": {
            "status": release_gate,
            "rule": (
                "Block when any regression test fails or errors."
            ),
        },
        "failed_tests": failed_tests,
        "test_results": test_results,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a pytest JSON report into an "
            "AI evaluation release-gate summary."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the pytest JSON report.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the generated summary.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    input_path = arguments.input.resolve()
    output_path = arguments.output.resolve()

    if not input_path.exists():
        raise FileNotFoundError(
            f"Pytest report not found: {input_path}"
        )

    pytest_report = load_json(input_path)
    summary = build_summary(
        pytest_report,
        input_path,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(summary, file, indent=2)
        file.write("\n")

    results = summary["results"]
    gate = summary["release_gate"]["status"]

    print("AI Evaluation Automation Summary")
    print("=" * 60)
    print(f'Total tests: {results["total"]}')
    print(f'Passed: {results["passed"]}')
    print(f'Failed: {results["failed"]}')
    print(f'Errors: {results["errors"]}')
    print(
        "Pass rate:",
        f'{results["pass_rate_percent"]:.2f}%',
    )
    print(f"Release gate: {gate}")
    print(f"Summary saved to: {output_path}")

    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())