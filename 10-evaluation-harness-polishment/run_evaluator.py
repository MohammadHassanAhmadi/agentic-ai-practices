import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from shared_tools import utiles as shareTool


shareTool.configure_utf8_output()


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"


class RegressionStatus(Enum):
    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED = "unchanged"
    NEW = "new"
    REMOVED = "removed"


@dataclass
class CaseComparison:
    case_id: str
    old_pass_rate: float | None
    new_pass_rate: float | None
    old_avg_duration: float | None
    new_avg_duration: float | None
    status: RegressionStatus


def get_report_cases(report: dict) -> list[dict]:
    cases = report.get("cases")
    if cases is None:
        cases = report.get("case")
    if cases is None:
        raise ValueError("Report must contain a 'cases' list")
    return cases


def compare_reports(old_report: dict, new_report: dict) -> list[CaseComparison]:
    old_cases = {case["case_id"]: case for case in get_report_cases(old_report)}
    new_cases = {case["case_id"]: case for case in get_report_cases(new_report)}

    comparisons: list[CaseComparison] = []

    all_case_ids = set(old_cases) | set(new_cases)

    for case_id in all_case_ids:
        old_case = old_cases.get(case_id)
        new_case = new_cases.get(case_id)

        if old_case is None:
            status = RegressionStatus.NEW

        elif new_case is None:
            status = RegressionStatus.REMOVED

        elif new_case["pass_rate"] > old_case["pass_rate"]:
            status = RegressionStatus.IMPROVED

        elif new_case["pass_rate"] < old_case["pass_rate"]:
            status = RegressionStatus.REGRESSED

        else:
            status = RegressionStatus.UNCHANGED

        comparisons.append(
            CaseComparison(
                case_id=case_id,
                status=status,
                old_pass_rate=old_case["pass_rate"] if old_case else None,
                new_pass_rate=new_case["pass_rate"] if new_case else None,
                old_avg_duration=(
                    old_case.get("avg_duration_seconds") if old_case else None
                ),
                new_avg_duration=(
                    new_case.get("avg_duration_seconds") if new_case else None
                ),
            )
        )
    return comparisons


def print_comparison_summary(
    comparisons: list[CaseComparison],
) -> None:
    improved = sum(item.status == RegressionStatus.IMPROVED for item in comparisons)

    regressed = sum(item.status == RegressionStatus.REGRESSED for item in comparisons)

    unchanged = sum(item.status == RegressionStatus.UNCHANGED for item in comparisons)
    new = sum(item.status == RegressionStatus.NEW for item in comparisons)
    removed = sum(item.status == RegressionStatus.REMOVED for item in comparisons)

    print()
    shareTool.print_color(f"Improved:  {improved}", shareTool.Color.GREEN)

    shareTool.print_color(f"Regressed: {regressed}", shareTool.Color.YELLOW)
    shareTool.print_color(f"Unchanged: {unchanged}", shareTool.Color.WHITE)
    shareTool.print_color(f"New:       {new}", shareTool.Color.WHITE)
    shareTool.print_color(f"Removed:   {removed}", shareTool.Color.WHITE)


def get_latest_reports() -> tuple[Path, Path] | None:
    files = list(RESULTS_DIR.glob("run_*.json"))

    if len(files) < 2:
        return None

    files.sort(
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    return files[1], files[0]


def load_report(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    latest_reports = get_latest_reports()

    if latest_reports is None:
        print("At least 2 reports are required.")
        return

    old_path, new_path = latest_reports

    old_report = load_report(str(old_path))
    new_report = load_report(str(new_path))

    comparisons = compare_reports(
        old_report,
        new_report,
    )

    for item in comparisons:
        old_rate = "-" if item.old_pass_rate is None else f"{item.old_pass_rate:.0%}"
        new_rate = "-" if item.new_pass_rate is None else f"{item.new_pass_rate:.0%}"

        old_duration = (
            "-" if item.old_avg_duration is None else f"{item.old_avg_duration:.2f}s"
        )

        new_duration = (
            "-" if item.new_avg_duration is None else f"{item.new_avg_duration:.2f}s"
        )

        print(
            f"{item.case_id}: "
            f"{old_rate} → {new_rate} "
            f"| {old_duration} → {new_duration} "
            f"| {item.status.value.upper()}"
        )

    print_comparison_summary(comparisons)


if __name__ == "__main__":
    main()
