"""Build the manuscript-described multi-experiment EEG-BIDS release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .brainvision import copy_brainvision, header_metadata, markers
from .config import EXPERIMENTS, recording_paths, source_paths

NA = "n/a"
PRIME = {1: "W+M+", 2: "W-M+", 3: "W-M-", 4: "semantic-only", 5: "unrelated"}


def write_tsv(rows, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, sep="\t", index=False, na_rep=NA)


def behavior_trials(df: pd.DataFrame, exp, subject: int) -> pd.DataFrame:
    rows = df[df["Subject"] == exp.behavior_id(subject)].copy()
    rows = rows.iloc[exp.practice_rows(subject):].reset_index(drop=True)
    if exp.id == 2 and subject == 2:
        rows = pd.concat([rows.iloc[:221], rows.iloc[225:]], ignore_index=True)
    return rows


def stimulus_markers(all_markers: list[dict]) -> list[dict]:
    return [m for m in all_markers if m["type"] == "Stimulus"
            and m["description"].replace(" ", "") not in {"S100", "S200"}]


def response_after(all_markers: list[dict], target: dict) -> dict | None:
    for marker in all_markers:
        if marker["sample"] > target["sample"] and marker["description"].replace(" ", "") in {"S100", "S200"}:
            return marker
        if marker["sample"] > target["sample"] and marker["type"] == "Stimulus":
            return None
    return None


def trial_rows(behavior: pd.DataFrame, all_markers: list[dict], exp, participant: str,
               sfreq: float, start_index: int = 1, run: int = 1) -> list[dict]:
    targets = stimulus_markers(all_markers)
    if len(targets) != len(behavior):
        raise ValueError(f"{participant}: {len(targets)} EEG target markers != {len(behavior)} behavioral trials")
    output = []
    for local_i, (target, (_, row)) in enumerate(zip(targets, behavior.iterrows()), start=1):
        i = start_index + local_i - 1
        trigger = int(target["description"].replace("S", "").strip())
        stim_type = int(row["StimType"])
        if trigger != stim_type:
            raise ValueError(f"{participant} trial {i}: marker {trigger} != StimType {stim_type}")
        response = response_after(all_markers, target)
        rt_ms = pd.to_numeric(row.get("Judge1.RT"), errors="coerce")
        recorded_rt = ((response["sample"] - target["sample"]) / sfreq * 1000) if response else None
        lexical = "word" if stim_type // 10 == 1 else "pseudoword"
        condition_digit = stim_type % 10
        output.append({
            "onset": (target["sample"] - 1) / sfreq, "duration": 0,
            "trial_type": "target", "value": trigger, "sample": target["sample"] - 1,
            "participant_id": f"sub-{participant}", "experiment": exp.id,
            "acquisition": exp.acquisition, "block": (i - 1) // 110 + 1,
            "run": run, "trial_index": i, "trial_in_block": (i - 1) % 110 + 1,
            "stimulus_id": row.get("StimNo", NA), "target_lexicality": lexical,
            "prime_condition": PRIME.get(condition_digit, "filler"),
            "masking_context": exp.masking_context, "prime_duration_ms": exp.prime_duration_ms,
            "preprime_display": exp.preprime_display, "prime_string": row.get("Stimulus2", NA),
            "target_string": row.get("Stimulus1", NA), "expected_response": row.get("Answer", NA),
            "response": row.get("Judge1.RESP", NA), "accuracy": row.get("Judge1.ACC", NA),
            "response_time_ms": rt_ms, "recorded_response_time_ms": recorded_rt,
            "response_marker": response["description"].replace(" ", "") if response else NA,
            "response_sample": response["sample"] - 1 if response else NA,
            "timing_source": "target_and_response_recorded;prime_and_preprime_reconstructed",
            "response_before_300ms": bool(pd.notna(rt_ms) and rt_ms < 300),
            "response_before_500ms": bool(pd.notna(rt_ms) and rt_ms < 500),
            "response_before_800ms": bool(pd.notna(rt_ms) and rt_ms < 800),
        })
    deltas = [r["recorded_response_time_ms"] - r["response_time_ms"] for r in output
              if pd.notna(r["recorded_response_time_ms"]) and pd.notna(r["response_time_ms"])]
    trigger_offset = float(pd.Series(deltas).median()) if deltas else None
    for row in output:
        row["response_trigger_offset_ms"] = trigger_offset
        row["response_time_residual_ms"] = (
            row["recorded_response_time_ms"] - trigger_offset - row["response_time_ms"]
            if trigger_offset is not None and pd.notna(row["recorded_response_time_ms"])
            and pd.notna(row["response_time_ms"]) else None
        )
    return output


def sidecars(root: Path) -> None:
    (root / "dataset_description.json").write_text(json.dumps({
        "Name": "Trial-resolved EEG and behavioral data across three experiments on masked and unmasked Chinese word priming",
        "BIDSVersion": "1.10.0", "DatasetType": "raw",
        "License": "PENDING_AUTHOR_APPROVAL",
        "Authors": ["PENDING_FINAL_AUTHOR_LIST"],
        "GeneratedBy": [{"Name": "scientific-data-code", "Version": "unreleased"}],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "README").write_text("Continuous EEG is unfiltered and otherwise unmodified from native BrainVision files.\nSee code/README.md and derivatives/ for processing and validation records.\n", encoding="utf-8")
    (root / "CHANGES").write_text("0.1.0 - Initial generated review snapshot; not approved for public release.\n", encoding="utf-8")
    event_defs = {key: {"Description": key.replace("_", " ")} for key in [
        "trial_type", "value", "participant_id", "experiment", "acquisition", "run", "block",
        "trial_index", "trial_in_block", "stimulus_id", "target_lexicality", "prime_condition",
        "masking_context", "prime_duration_ms", "preprime_display", "prime_string", "target_string",
        "expected_response", "response", "accuracy", "response_time_ms", "recorded_response_time_ms",
        "response_trigger_offset_ms", "response_time_residual_ms", "response_marker", "response_sample",
        "timing_source", "response_before_300ms",
        "response_before_500ms", "response_before_800ms"]}
    (root / "task-lexdec_events.json").write_text(json.dumps(event_defs, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def build(source_root: Path, output_root: Path, copy_eeg: bool = True, limit: int | None = None) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    sidecars(output_root)
    participants, all_trials, source_map, channel_rows = [], [], [], []
    for exp in EXPERIMENTS.values():
        _, behavior_path = source_paths(source_root, exp, exp.subject_ids[0])
        behavior = pd.read_excel(behavior_path)
        subjects = exp.subject_ids[:limit] if limit else exp.subject_ids
        for subject in subjects:
            participant = exp.participant(subject)
            subject_behavior = behavior_trials(behavior, exp, subject)
            behavior_cursor = 0
            participant_trials = []
            recording_summaries = []
            for run, vhdr in enumerate(recording_paths(source_root, exp, subject), start=1):
                run_entity = f"_run-{run:02d}" if len(recording_paths(source_root, exp, subject)) > 1 else ""
                stem_name = f"sub-{participant}_task-lexdec_acq-{exp.acquisition}{run_entity}_eeg"
                eeg_dir = output_root / f"sub-{participant}" / "eeg"
                meta = copy_brainvision(vhdr, eeg_dir / stem_name) if copy_eeg else header_metadata(vhdr)
                if not copy_eeg:
                    eeg_file = vhdr.parent / meta["data_file"]
                    meta["n_samples"] = eeg_file.stat().st_size // (meta["n_channels"] * 2)
                    meta["duration_s"] = meta["n_samples"] / meta["sampling_frequency"]
                    meta["source_vmrk"] = vhdr.parent / meta["marker_file"]
                raw_markers = markers(Path(meta["source_vmrk"]))
                n_targets = len(stimulus_markers(raw_markers))
                run_behavior = subject_behavior.iloc[behavior_cursor:behavior_cursor + n_targets]
                trials = trial_rows(run_behavior, raw_markers, exp, participant,
                                    meta["sampling_frequency"], behavior_cursor + 1, run)
                behavior_cursor += n_targets
                participant_trials.extend(trials)
                events_path = eeg_dir / stem_name.replace("_eeg", "_events.tsv")
                write_tsv(trials, events_path)
                channels = []
                for ch in meta["channels"]:
                    kind = "EOG" if ch["name"] in {"HEOG", "VEOG"} else "EEG"
                    channels.append({"name": ch["name"], "type": kind, "units": "uV",
                                     "sampling_frequency": meta["sampling_frequency"],
                                     "status": "good", "status_description": NA})
                    channel_rows.append({"participant_id": f"sub-{participant}", "run": run, **channels[-1]})
                write_tsv(channels, eeg_dir / stem_name.replace("_eeg", "_channels.tsv"))
                eeg_json = {"TaskName": "lexdec", "SamplingFrequency": meta["sampling_frequency"],
                            "PowerLineFrequency": 50, "SoftwareFilters": "n/a",
                            "EEGReference": "native acquisition reference; final value requires author confirmation",
                            "EEGGround": "PENDING_AUTHOR_CONFIRMATION", "EEGChannelCount": sum(c["type"] == "EEG" for c in channels),
                            "EOGChannelCount": sum(c["type"] == "EOG" for c in channels),
                            "RecordingType": "continuous", "RecordingDuration": meta["duration_s"]}
                (eeg_dir / stem_name.replace("_eeg", "_eeg.json")).write_text(json.dumps(eeg_json, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                source_map.append({"participant_id": f"sub-{participant}", "run": run,
                                   "native_vhdr": str(vhdr.relative_to(source_root)),
                                   "native_behavior_file": str(behavior_path.relative_to(source_root)),
                                   "native_behavior_subject": exp.behavior_id(subject),
                                   "practice_rows_removed": exp.practice_rows(subject),
                                   "special_correction": "removed_behavior_rows_222_to_225" if exp.id == 2 and subject == 2 else NA,
                                   "n_channels": meta["n_channels"], "sampling_frequency": meta["sampling_frequency"],
                                   "recording_duration_s": meta["duration_s"], "n_trials": len(trials)})
                recording_summaries.append(meta)
            if behavior_cursor != len(subject_behavior):
                raise ValueError(f"{participant}: recordings contain {behavior_cursor} trials but behavior has {len(subject_behavior)}")
            participants.append({"participant_id": f"sub-{participant}", "experiment": exp.id,
                                 "native_subject_code": subject, "sex": NA, "age": NA,
                                 "handedness": "right", "release_status": "pending_ethics_authorization"})
            all_trials.extend(participant_trials)
    write_tsv(participants, output_root / "participants.tsv")
    (output_root / "participants.json").write_text(json.dumps({k: {"Description": k.replace("_", " ")} for k in participants[0]}, indent=2)+"\n", encoding="utf-8")
    deriv = output_root / "derivatives" / "trial-resolved"
    write_tsv(all_trials, deriv / "trial_resolved_eeg_behavior.tsv")
    write_tsv(source_map, output_root / "sourcedata" / "native_to_bids_mapping.tsv")
    write_tsv(channel_rows, output_root / "derivatives" / "quality-control" / "channel_inventory.tsv")
    stimuli_cols = ["stimulus_id", "target_lexicality", "prime_condition", "prime_string", "target_string"]
    stimuli = pd.DataFrame(all_trials)[stimuli_cols].drop_duplicates()
    stimuli.to_csv(output_root / "stimuli.tsv", sep="\t", index=False, na_rep=NA)
    dictionary = [{"column": c, "description": c.replace("_", " "), "missing_value": NA}
                  for c in pd.DataFrame(all_trials).columns]
    write_tsv(dictionary, deriv / "data_dictionary.tsv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--no-copy-eeg", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    build(args.source_root.resolve(), args.output_root.resolve(), not args.no_copy_eeg, args.limit)


if __name__ == "__main__":
    main()
