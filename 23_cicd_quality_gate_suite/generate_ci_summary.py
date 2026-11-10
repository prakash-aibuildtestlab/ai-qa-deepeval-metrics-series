import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = MODULE_DIR / "quality_gate_config.json"


def load_json(file_path: Path) -> dict:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def calculate_stage_result(stage: dict) -> dict:
    report_path = MODULE_DIR / stage["report_file"]

    result = {
        "name": stage["name"],
        "marker": stage["marker"],
        "description": stage["description"],
        "blocking": stage["blocking"],
        "minimum_pass_rate": stage["minimum_pass_rate"],
        "report_file": str(report_path),
        "report_found": report_path.exists(),
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "pass_rate": 0.0,
        "pytest_exit_code": None,
        "result": "BLOCK",
        "reasons": [],
    }

    if not report_path.exists():
        result["reasons"].append("Pytest JSON report was not found.")
        return result

    try:
        report = load_json(report_path)
    except (OSError, json.JSONDecodeError) as error:
        result["reasons"].append(
            f"Unable to read pytest report: {error}"
        )
        return result

    summary = report.get("summary", {})

    result["total"] = int(summary.get("total", 0))
    result["passed"] = int(summary.get("passed", 0))
    result["failed"] = int(summary.get("failed", 0))

    result["errors"] = int(
        summary.get(
            "error",
            summary.get("errors", 0),
        )
    )

    result["skipped"] = int(summary.get("skipped", 0))
    result["pytest_exit_code"] = report.get("exitcode")

    if result["total"] > 0:
        result["pass_rate"] = (
            result["passed"] / result["total"]
        )

    if result["total"] == 0:
        result["reasons"].append(
            "No tests were executed for this stage."
        )

    if result["failed"] > 0:
        result["reasons"].append(
            f'{result["failed"]} test failure(s) detected.'
        )

    if result["errors"] > 0:
        result["reasons"].append(
            f'{result["errors"]} test error(s) detected.'
        )

    if result["pytest_exit_code"] not in (0, None):
        result["reasons"].append(
            "Pytest returned a non-zero exit code: "
            f'{result["pytest_exit_code"]}.'
        )

    if result["pass_rate"] < stage["minimum_pass_rate"]:
        result["reasons"].append(
            "Pass rate "
            f'{result["pass_rate"]:.2%} is below the required '
            f'{stage["minimum_pass_rate"]:.2%}.'
        )

    if not result["reasons"]:
        result["result"] = "PASS"

    return result


def create_markdown_summary(summary: dict) -> str:
    lines = [
        "# AI Evaluation CI Quality Gate",
        "",
        f'**Release gate:** {summary["release_gate"]}',
        "",
        "| Stage | Tests | Passed | Failed | Errors | "
        "Pass rate | Required | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for stage in summary["stages"]:
        lines.append(
            f'| {stage["name"]} '
            f'| {stage["total"]} '
            f'| {stage["passed"]} '
            f'| {stage["failed"]} '
            f'| {stage["errors"]} '
            f'| {stage["pass_rate"]:.2%} '
            f'| {stage["minimum_pass_rate"]:.2%} '
            f'| {stage["result"]} |'
        )

    lines.extend(
        [
            "",
            f'**Total tests:** {summary["totals"]["total"]}',
            "",
            f'**Passed:** {summary["totals"]["passed"]}',
            "",
            f'**Failed:** {summary["totals"]["failed"]}',
            "",
            f'**Errors:** {summary["totals"]["errors"]}',
        ]
    )

    blocked_stages = [
        stage
        for stage in summary["stages"]
        if stage["blocking"] and stage["result"] != "PASS"
    ]

    if blocked_stages:
        lines.extend(["", "## Blocking reasons", ""])

        for stage in blocked_stages:
            lines.append(f'### {stage["name"].upper()}')

            for reason in stage["reasons"]:
                lines.append(f"- {reason}")

            lines.append("")

    return "\n".join(lines)


def write_github_step_summary(markdown: str) -> None:
    github_summary_file = os.getenv("GITHUB_STEP_SUMMARY")

    if not github_summary_file:
        return

    with Path(github_summary_file).open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(markdown)
        file.write("\n")


def main() -> int:
    if not CONFIG_FILE.exists():
        print(
            f"Configuration file not found: {CONFIG_FILE}",
            file=sys.stderr,
        )
        return 2

    try:
        config = load_json(CONFIG_FILE)
    except (OSError, json.JSONDecodeError) as error:
        print(
            f"Unable to read quality-gate configuration: {error}",
            file=sys.stderr,
        )
        return 2

    stage_results = [
        calculate_stage_result(stage)
        for stage in config["stages"]
    ]

    blocking_failures = [
        stage
        for stage in stage_results
        if stage["blocking"] and stage["result"] != "PASS"
    ]

    totals = {
        "total": sum(stage["total"] for stage in stage_results),
        "passed": sum(stage["passed"] for stage in stage_results),
        "failed": sum(stage["failed"] for stage in stage_results),
        "errors": sum(stage["errors"] for stage in stage_results),
        "skipped": sum(stage["skipped"] for stage in stage_results),
    }

    release_gate = (
        "PASS"
        if not blocking_failures
        else "BLOCK"
    )

    summary = {
        "quality_gate_name": config["quality_gate_name"],
        "config_version": config["config_version"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "release_gate": release_gate,
        "blocking_failure_count": len(blocking_failures),
        "totals": totals,
        "stages": stage_results,
    }

    reports_directory = MODULE_DIR / "reports"
    reports_directory.mkdir(parents=True, exist_ok=True)

    summary_file = (
        MODULE_DIR
        / config["reporting"]["summary_file"]
    )

    with summary_file.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
        file.write("\n")

    markdown = create_markdown_summary(summary)

    local_markdown_file = (
        reports_directory
        / "github_step_summary.md"
    )

    local_markdown_file.write_text(
        markdown + "\n",
        encoding="utf-8",
    )

    write_github_step_summary(markdown)

    print("AI Evaluation CI Quality Gate")
    print("=" * 60)

    for stage in stage_results:
        print(
            f'{stage["name"].upper():<12}'
            f'Tests: {stage["total"]:<3} '
            f'Passed: {stage["passed"]:<3} '
            f'Failed: {stage["failed"]:<3} '
            f'Pass rate: {stage["pass_rate"]:.2%} '
            f'Result: {stage["result"]}'
        )

    print("=" * 60)
    print(f"Release gate: {release_gate}")
    print(f"Summary saved to: {summary_file}")

    return config["exit_codes"][
        "pass" if release_gate == "PASS" else "block"
    ]


if __name__ == "__main__":
    raise SystemExit(main())