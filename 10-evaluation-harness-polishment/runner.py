import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from statistics import mean
from typing import Protocol

import tools
from app import AgentRun, RunStatus, ToolCall, client, model, run_agent_for_runner
from pydantic import BaseModel

from shared_tools.utiles import Color, print_color

BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"
RESULTS_DIR = BASE_DIR / "results"


class ScoreStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class Expected:
    tool_calls: list[ToolCall] = field(default_factory=list)
    max_iterations: int | None = None
    answer_rubric: str | None = None


@dataclass
class TestCase:
    id: str
    input: str
    scorer: list[str]
    expected: Expected
    setup: dict | None = None


@dataclass
class ScoreResult:
    scorer: str
    status: ScoreStatus
    reason: str


class Scorer(Protocol):
    def score(self, case: TestCase, result: AgentRun) -> ScoreResult: ...


# Expected:
# A → B → C

# if Actual:
# X → A → Y → B → C → Z => PASS

# if Actual:
# B → A → C => FAIL


class LLMJudgeResult(BaseModel):
    status: ScoreStatus
    reason: str
    score: float


@dataclass
class WorkspaceSnapshot:
    files: dict[Path, bytes]
    directories: set[Path]


def setup_case(case: TestCase) -> None:
    if not case.setup:
        return

    create_files = case.setup.get("create_files", {})

    for filename, content in create_files.items():
        file_path = tools.safe_path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def cleanup_case(case: TestCase) -> None:
    if not case.setup:
        return

    create_files = case.setup.get("create_files", {})

    for filename in create_files:
        file_path = tools.WORKSPACE_PATH / filename

        if file_path.exists():
            file_path.unlink()


def has_exact_call_order(
    expected_calls: list[ToolCall], actual_calls: list[ToolCall]
) -> bool:
    if not expected_calls:
        return False

    expected_index = 0

    for actual in actual_calls:
        expected = expected_calls[expected_index]
        if actual.name == expected.name:
            expected_index += 1

            if expected_index == len(expected_calls):
                return True

    return False


class ToolOrderScorer:
    def score(self, case: TestCase, result: AgentRun) -> ScoreResult:

        expected_calls = case.expected.tool_calls
        scorer = "tool_order"
        if len(expected_calls) < 2:
            return ScoreResult(
                scorer="tool_order",
                reason="At least 2 expected tool calls are required",
                status=ScoreStatus.ERROR,
            )

        if has_exact_call_order(expected_calls, result.tools_called):
            return ScoreResult(
                scorer=scorer,
                reason="Expected tool order matched",
                status=ScoreStatus.PASS,
            )

        return ScoreResult(
            scorer=scorer,
            reason="Expected tool order did not match",
            status=ScoreStatus.FAIL,
        )


class ToolCallScorer:
    def score(self, case: TestCase, result: AgentRun) -> ScoreResult:
        scorer = "tool_called"
        expected_calls = case.expected.tool_calls

        if not expected_calls:
            return ScoreResult(
                reason="Expected tool_calls are missing",
                scorer=scorer,
                status=ScoreStatus.ERROR,
            )

        matched_actual_indexes: set[int] = set()

        for expected in expected_calls:
            matched = False

            for index, actual in enumerate(result.tools_called):
                if index in matched_actual_indexes:
                    continue

                same_name = actual.name == expected.name
                same_arguments = not expected.arguments or all(
                    actual.arguments.get(name) == value
                    for name, value in expected.arguments.items()
                )
                if same_name and same_arguments:
                    matched = True
                    matched_actual_indexes.add(index)
                    break

            if not matched:
                return ScoreResult(
                    scorer=scorer,
                    reason=f"Expected tool call not found: {expected.name}",
                    status=ScoreStatus.FAIL,
                )

        return ScoreResult(
            scorer=scorer,
            status=ScoreStatus.PASS,
            reason="All expected tool calls were found",
        )


##################################################################


@dataclass
class RunEvaluation:
    status: ScoreStatus
    scores: list[ScoreResult]
    iterations: int
    duration_seconds: float
    reason: str = ""


@dataclass
class CaseResult:
    case_id: str
    runs: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    avg_iterations: float
    max_iterations: int
    run_evaluations: list[RunEvaluation]
    avg_duration_seconds: float


class MaxIterationsScorer:
    def score(self, case: TestCase, result: AgentRun) -> ScoreResult:
        expected_max_iterations = case.expected.max_iterations

        if expected_max_iterations is None:
            return ScoreResult(
                reason="max_iterations is missing",
                scorer="max_iterations",
                status=ScoreStatus.ERROR,
            )

        passed = expected_max_iterations >= result.iterations

        return ScoreResult(
            scorer="max_iterations",
            status=ScoreStatus.PASS if passed else ScoreStatus.FAIL,
            reason=(
                f"{result.iterations} <= {expected_max_iterations}"
                if passed
                else f"Expected <= {expected_max_iterations}, actual {result.iterations}"
            ),
        )


class LLMJudgeScorer:
    def score(self, case: TestCase, result: AgentRun) -> ScoreResult:
        scorer = "llm_judge"
        rubric = case.expected.answer_rubric

        if rubric is None:
            return ScoreResult(
                scorer=scorer,
                reason="answer_rubric is missing",
                status=ScoreStatus.ERROR,
            )

        prompt = f"""
Evaluate this agent answer.

Rubric:
{rubric}

Agent answer:
{result.result}
        """
        response = client.responses.parse(
            model=model, input=prompt, text_format=LLMJudgeResult
        )
        judge_result = response.output_parsed

        if judge_result is None:
            return ScoreResult(
                status=ScoreStatus.ERROR,
                scorer=scorer,
                reason="LLM judge returned no structured result",
            )

        return ScoreResult(
            status=judge_result.status,
            scorer=scorer,
            reason=(f"{judge_result.reason} (score: {judge_result.score:.2f})"),
        )


SCORERS = {
    "tool_called": ToolCallScorer(),
    "max_iterations": MaxIterationsScorer(),
    "llm_judge": LLMJudgeScorer(),
    "tool_order": ToolOrderScorer(),
}


def validate_case(case: TestCase) -> list[str]:
    errors: list[str] = []

    if not case.id.strip():
        errors.append("id must not be empty")

    if not case.input.strip():
        errors.append("input must not be empty")

    if not case.scorer:
        errors.append("At least one scorer is required")

    for scorer_name in case.scorer:
        if scorer_name not in SCORERS:
            errors.append(f"Unknown scorer: {scorer_name}")

    if "tool_called" in case.scorer and not case.expected.tool_calls:
        errors.append("tool_called requires expected.tool_calls")

    if "tool_order" in case.scorer and len(case.expected.tool_calls) < 2:
        errors.append("tool_order requires at least 2 expected tool calls")

    if "max_iterations" in case.scorer and case.expected.max_iterations is None:
        errors.append("max_iterations requires expected.max_iterations")

    if "llm_judge" in case.scorer and case.expected.answer_rubric is None:
        errors.append("llm_judge requires expected.answer_rubric")

    return errors


def parse_test_case(data: dict) -> TestCase:

    tool_calls_data = data["expected"].get("tool_calls")
    expected_tool_calls: list[ToolCall] = []
    if tool_calls_data:
        expected_tool_calls = [ToolCall(**tool_data) for tool_data in tool_calls_data]

    expected = Expected(
        tool_calls=expected_tool_calls,
        max_iterations=data["expected"].get("max_iterations"),
        answer_rubric=data["expected"].get("answer_rubric"),
    )

    return TestCase(
        id=data["id"],
        input=data["input"],
        expected=expected,
        scorer=data["scorers"],
        setup=data.get("setup"),
    )


def load_cases(cases_dir: Path = CASES_DIR) -> list[TestCase]:
    cases: list[TestCase] = []
    for file in sorted(cases_dir.glob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            cases.append(parse_test_case(data))
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            print_color(
                f"{file.name}: INVALID — {type(error).__name__}: {error}",
                Color.RED,
            )

    return cases


def save_report(case_results: list[CaseResult], overall_pass_rate: float):
    RESULTS_DIR.mkdir(exist_ok=True)

    report = {
        "overall_pass_rate": overall_pass_rate,
        "cases": [asdict(result) for result in case_results],
    }

    filename = datetime.now().strftime("run_%Y%m%d_%H%M%S_%f.json")
    (RESULTS_DIR / filename).write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_run_status(scores: list[ScoreResult]) -> ScoreStatus:
    if any(score.status == ScoreStatus.ERROR for score in scores):
        return ScoreStatus.ERROR

    if any(score.status == ScoreStatus.FAIL for score in scores):
        return ScoreStatus.FAIL

    return ScoreStatus.PASS


def build_case_result(
    case: TestCase, run_evaluations: list[RunEvaluation]
) -> CaseResult:
    if not run_evaluations:
        raise ValueError("At least one run evaluation is required")

    passed = sum(run.status == ScoreStatus.PASS for run in run_evaluations)
    failed = sum(run.status == ScoreStatus.FAIL for run in run_evaluations)
    errors = sum(run.status == ScoreStatus.ERROR for run in run_evaluations)

    return CaseResult(
        case_id=case.id,
        runs=len(run_evaluations),
        pass_rate=passed / len(run_evaluations),
        avg_iterations=mean(run.iterations for run in run_evaluations),
        max_iterations=max(run.iterations for run in run_evaluations),
        passed=passed,
        run_evaluations=run_evaluations,
        errors=errors,
        failed=failed,
        avg_duration_seconds=mean(run.duration_seconds for run in run_evaluations),
    )


def evaluate_run(case: TestCase) -> RunEvaluation:

    start_time = time.perf_counter()

    try:
        setup_case(case)
        run_result = run_agent_for_runner(case.input)
        elapsed = time.perf_counter() - start_time

        if run_result.status != RunStatus.SUCCESS:
            evaluation = RunEvaluation(
                status=ScoreStatus.FAIL,
                scores=[],
                iterations=run_result.iterations,
                reason=(
                    "Agent run failed with error "
                    f"{run_result.error_code}: {run_result.result}"
                ),
                duration_seconds=elapsed,
            )
        else:
            scores = [SCORERS[name].score(case, run_result) for name in case.scorer]
            evaluation = RunEvaluation(
                status=get_run_status(scores),
                scores=scores,
                iterations=run_result.iterations,
                duration_seconds=elapsed,
            )
    except Exception as error:
        evaluation = RunEvaluation(
            status=ScoreStatus.ERROR,
            scores=[],
            iterations=0,
            duration_seconds=time.perf_counter() - start_time,
            reason=f"Runner error: {type(error).__name__}: {error}",
        )
    finally:
        cleanup_case(case)

    return evaluation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--case")

    args = parser.parse_args()
    if args.runs <= 0:
        print_color("--runs must be greater than zero", Color.YELLOW)
        return 1

    all_cases = load_cases()

    if args.case:
        all_cases = [c for c in all_cases if c.id == args.case]

    if len(all_cases) == 0:
        message = (
            f"No case matched with case:{args.case}"
            if args.case
            else f"No test cases found in {CASES_DIR}"
        )
        print_color(message, Color.YELLOW)
        return 1

    valid_cases: list[TestCase] = []

    for case in all_cases:
        errors = validate_case(case=case)
        if errors:
            print(f"{case.id}: INVALID — {'; '.join(errors)}")
            continue

        valid_cases.append(case)

    if not valid_cases:
        print_color("No valid cases to run", Color.YELLOW)
        return 1

    case_results: list[CaseResult] = []

    for case in valid_cases:
        run_evaluations = [evaluate_run(case) for _ in range(args.runs)]
        case_result = build_case_result(case, run_evaluations)
        case_results.append(case_result)

        print(
            f"{case_result.case_id}: "
            f"{case_result.pass_rate:.0%} "
            f"({case_result.passed}/{case_result.runs} passed, "
            f"{case_result.failed} failed, {case_result.errors} errors)"
        )

    overall_pass_rate = mean(case.pass_rate for case in case_results)
    print(f"\nOverall pass rate: {overall_pass_rate:.0%}")

    save_report(case_results, overall_pass_rate)
    return 0 if all(case.pass_rate == 1.0 for case in case_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
