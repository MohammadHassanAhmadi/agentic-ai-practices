import json
from pathlib import Path


def load_report(path: str) -> dict:
    return json.loads(Path(path).read_text())


old_report = load_report("results/old.json")
old_report = load_report("results/new.json")


old_cases = {case["case_id"]: case for case in old_report["cases"]}
new_cases = {case["case_id"]: case for case in old_report["cases"]}


for case_id, new_case in new_cases.items():
    old_case = old_cases.get(case_id)

    if old_case is None:
        print(f"{case_id}: NEW CASE")
        continue

    difference = new_case["pass_rate"] - old_case["pass_rate"]

    print(
        f"{case_id}: "
        f"{old_case['pass_rate']:.0%} → "
        f"{new_case['pass_rate']:.0%} "
        f"({difference:+.0%})"
    )
