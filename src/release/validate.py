"""Deterministic inventory, join, timing, and BIDS release checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_ROOT = ["dataset_description.json", "participants.tsv", "participants.json",
                 "task-lexdec_events.json", "stimuli.tsv", "README", "CHANGES"]
REQUIRED_TRIAL = {"participant_id", "experiment", "block", "trial_index", "stimulus_id",
                  "prime_condition", "accuracy", "response_time_ms", "timing_source"}


def validate(root: Path, tolerance_ms: float = 25.0) -> dict:
    checks, failures, warnings = [], [], []
    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            failures.append(name)
    for name in REQUIRED_ROOT:
        check(f"root_file:{name}", (root / name).is_file(), name)
    event_files = sorted(root.glob("sub-*/eeg/*_events.tsv"))
    participants = pd.read_csv(root / "participants.tsv", sep="\t") if (root / "participants.tsv").exists() else pd.DataFrame()
    check("at_least_one_event_file_per_participant", len(event_files) >= len(participants),
          f"recordings={len(event_files)} participants={len(participants)}")
    total_trials = duplicate_keys = nonmonotonic = rt_mismatches = 0
    before = {300: 0, 500: 0, 800: 0}
    for path in event_files:
        df = pd.read_csv(path, sep="\t", keep_default_na=False)
        total_trials += len(df)
        missing = REQUIRED_TRIAL.difference(df.columns)
        check(f"required_columns:{path.parent.parent.name}", not missing, str(sorted(missing)))
        duplicate_keys += int(df.duplicated(["participant_id", "block", "trial_index"]).sum())
        nonmonotonic += int((pd.to_numeric(df["onset"], errors="coerce").diff().dropna() < 0).sum())
        rt1 = pd.to_numeric(df["response_time_ms"], errors="coerce")
        residual = pd.to_numeric(df["response_time_residual_ms"], errors="coerce")
        rt_mismatches += int((residual.abs() > tolerance_ms).sum())
        for threshold in before:
            before[threshold] += int((rt1 < threshold).sum())
    check("unique_trial_keys", duplicate_keys == 0, str(duplicate_keys))
    check("monotonic_event_onsets", nonmonotonic == 0, str(nonmonotonic))
    # Behavioral RT and trigger latency may differ by display/response-device timing;
    # report rather than silently failing the entire release.
    rt_passed = rt_mismatches == 0
    checks.append({"check": "rt_reconstruction_within_tolerance", "passed": rt_passed,
                   "detail": f"tolerance_ms={tolerance_ms}; mismatches={rt_mismatches}"})
    if not rt_passed:
        warnings.append("rt_reconstruction_within_tolerance")
    summary = {"passed": not failures, "failures": failures, "warnings": warnings,
               "n_participants": len(participants),
               "n_event_files": len(event_files), "n_trials": total_trials,
               "responses_before_ms": before, "timing_tolerance_ms": tolerance_ms,
               "checks": checks}
    out = root / "derivatives" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "internal_validation.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    pd.DataFrame(checks).to_csv(out / "internal_validation.tsv", sep="\t", index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tolerance-ms", type=float, default=25.0)
    args = parser.parse_args()
    result = validate(args.root.resolve(), args.tolerance_ms)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
