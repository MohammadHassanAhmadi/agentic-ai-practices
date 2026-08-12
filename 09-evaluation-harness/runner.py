import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from statistics import mean
from typing import Any, Protocol

from app import AgentRun, RunStatus, client, model, run_agent_for_runner


class ScoreStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ScoreResult:
    scorer: str
    status: ScoreStatus
    reason: str


class Scorer(Protocol):
    def score(self, case, result: AgentRun) -> ScoreResult: ...


class ToolCalledScorer:
    def score(self, case, result: AgentRun) -> ScoreResult:
        expected_tool = case["expected"]["tool"]
        passed = expected_tool["name"] in result.tools_called
        return ScoreResult(
            scorer="tool_called",
            status=ScoreStatus.ERROR,
            reason=("Tool was called" if passed else f"{expected_tool} was not called"),
        )


@dataclass
class RunEvaluation:
    status: ScoreStatus
    scores: list[ScoreResult]
    iterations: int
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


class MaxIterationsScorer:
    def score(self, case, result: AgentRun) -> ScoreResult:
        expected_max_iterations = case["expected"]["max_iterations"]
        passed = expected_max_iterations >= result.iterations

        return ScoreResult(
            scorer="max_iteration",
            status=ScoreStatus.PASS if passed else ScoreStatus.FAIL,
            reason=(
                f"{result.iterations} <= {expected_max_iterations}"
                if passed
                else f"Expected <= {expected_max_iterations}, actual {result.iterations}"
            ),
        )


class LLMJudgeScorer:
    def score(self, case: dict[str, Any], result: AgentRun) -> ScoreResult:
        rubric = case["expected"]["answer_rubric"]
        prompt = f"""
Evaluate this agent answer.

Rubric:
{rubric}

Agent answer:
{result.result}

Return only PASS or FAIL.
        """
        response = client.responses.create(model=model, input=prompt)
        passed = response.output_text.strip().upper() == "PASS"

        return ScoreResult(
            status=ScoreStatus.PASS if passed else ScoreStatus.FAIL,
            scorer="llm_judge",
            reason=response.output_text,
        )


def load_cases() -> list[dict]:
    cases: list[dict] = []
    for file in Path("cases").glob("*.json"):
        cases.append(json.loads(file.read_text()))

    return cases


def save_report(case_results: list[CaseResult], overall_pass_rate: float):
    Path("results").mkdir(exist_ok=True)

    report = {
        "overall_pass_rate": overall_pass_rate,
        "case": [asdict(result) for result in case_results],
    }

    filename = datetime.now().strftime("run_%Y%m%d_%H%M%S.json")
    Path("results", filename).write_text(json.dumps(report, indent=2))


def get_run_status(scores: list[ScoreResult]) -> ScoreStatus:
    if any(score.status == ScoreStatus.FAIL for score in scores):
        return ScoreStatus.FAIL

    if any(score.status == ScoreStatus.ERROR for score in scores):
        return ScoreStatus.ERROR

    return ScoreStatus.PASS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--case")

    args = parser.parse_args()
    cases = load_cases()

    if args.case:
        cases = [c for c in cases if c["id"] == args.case]

    case_results = []

    SCORERS = {
        "tool_called": ToolCalledScorer(),
        "max_iterations": MaxIterationsScorer(),
        "llm_judge": LLMJudgeScorer(),
    }
    for case in cases:
        results = []
        iterations = []
        run_evaluations = []
        for _ in range(args.runs):
            run_result = run_agent_for_runner(case["input"])
            if run_result.status != RunStatus.SUCCESS:
                results.append(
                    RunEvaluation(
                        status=ScoreStatus.FAIL,
                        scores=[],
                        iterations=run_result.iterations,
                        reason=f"agent run failed, with error: {run_result.error_code} and the result: {run_result.result}",
                    )
                )
                continue

            scores = []
            for name in case["scorers"]:
                scorer = SCORERS.get(name)
                if scorer is None:
                    scores.append(
                        ScoreResult(
                            status=ScoreStatus.ERROR,
                            reason=f"Unknown scorer:{name}",
                            scorer=name,
                        )
                    )
                    continue

                scores.append(scorer.score(case, run_result))

            passed = all(score.status == ScoreStatus.PASS for score in scores)
            results.append(passed)
            iterations.append(run_result.iterations)

            run_evaluations.append(
                RunEvaluation(
                    status=get_run_status(scores),
                    scores=scores,
                    iterations=run_result.iterations,
                )
            )

        case_result = CaseResult(
            case_id=case["id"],
            runs=len(results),
            pass_rate=mean(run.status == ScoreStatus.PASS for run in run_evaluations),
            avg_iterations=mean(run.iterations for run in run_evaluations),
            max_iterations=max(run.iterations for run in run_evaluations),
            run_evaluations=run_evaluations,
            passed=sum(run.status == ScoreStatus.PASS for run in run_evaluations),
            errors=sum(run.status == ScoreStatus.ERROR for run in run_evaluations),
            failed=sum(run.status == ScoreStatus.FAIL for run in run_evaluations),
        )
        case_results.append(case_result)

        print(
            f"{case_result.case_id}: "
            f"{case_result.pass_rate:.0%} "
            f"({case_result.passed}/{case_result.runs} passed)"
        )

    overall_pass_rate = mean(case.pass_rate for case in case_results)
    print(f"\nOverall pass rate: {overall_pass_rate:.0%}")

    save_report(case_results, overall_pass_rate)


if __name__ == "__main__":
    main()
