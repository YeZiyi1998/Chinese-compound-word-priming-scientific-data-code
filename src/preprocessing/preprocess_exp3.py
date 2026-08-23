"""Preprocess Experiment 3 (unmasked 200 ms).

Identical pipeline to Experiment 1 except for a -400 to 1000 ms epoch with a
-400 to -200 ms pre-prime baseline (matching the longer prime duration), and
the subject ids stored in the behavioral Excel use a ``3NN`` prefix.
"""

from __future__ import annotations

import json
from pathlib import Path

import mne
import numpy as np
import pandas as pd
import tqdm

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

SUB_LIST = list(range(1, 31))
EPOCH_TMIN = -0.4
EPOCH_TMAX = 1.0
BASELINE = (-0.4, -0.2)


REGION_CHANNELS = {
    "central": ["C1", "Cz", "C2", "CP1", "CPz", "CP2", "T7", "C5", "C3", "TP7",
                "CP5", "C4", "C6", "T8", "CP4", "CP6", "TP8"],
    "posterior": ["P7", "P5", "P3", "PO7", "PO3", "P1", "Pz", "P2", "O1", "POz",
                  "O2", "P4", "P6", "P8", "PO4", "PO8"],
    "Anterior": ["F3", "F5", "F7", "FC3", "FC5", "FT7", "F4", "F6", "F8", "FC4",
                 "FC6", "FT8", "Fz"],
    "All": ["F3", "F5", "F7", "FC3", "FC5", "FT7", "C3", "C5", "T7", "CP3",
            "CP5", "TP7", "P3", "P5", "P7", "PO3", "PO7", "F4", "F6", "F8",
            "FC4", "FC6", "FT8", "C4", "C6", "T8", "CP4", "CP6", "TP8", "P4",
            "P6", "P8", "PO4", "PO8", "Cz", "Pz", "Fz"],
    "dy": ["CP1", "CP2", "P3", "Pz", "P4", "PO3", "PO4"],
}


def _vhdr_path(sub: int) -> Path:
    return DATA / "exp3" / "实验3脑电数据" / f"3EXP{sub:02}.vhdr"


def _behavior_path() -> Path:
    return DATA / "exp3" / "实验三行为数据-unmask&SOA=200ms.xlsx"


def _output_path() -> Path:
    return DATA / "results" / "exp3_u2erp.json"


def preprocess_one(sub: int, csv_data: pd.DataFrame) -> dict:
    raw = mne.io.read_raw_brainvision(str(_vhdr_path(sub)), preload=True)
    region2index = {
        region: [raw.ch_names.index(ch) for ch in channels]
        for region, channels in REGION_CHANNELS.items()
    }
    raw.set_eeg_reference(["Right Mastoid", "Left Mastoid"])
    raw.apply_proj()
    raw = raw.filter(0.5, 30)

    onsets = raw.annotations.onset[1:] * 500
    durations = raw.annotations.duration[1:] * 500
    descriptions = raw.annotations.description[1:]

    non_reaction_index = [
        i for i in range(len(descriptions))
        if descriptions[i] not in {"Stimulus/S100", "Stimulus/S200"}
        and "Segment/" not in descriptions[i]
    ]
    onsets = [onsets[i] for i in range(len(onsets)) if i in non_reaction_index]
    durations = [durations[i] for i in range(len(durations)) if i in non_reaction_index]
    descriptions = [descriptions[i].split()[-1] for i in range(len(descriptions)) if i in non_reaction_index]

    sub_id = int(f"3{sub:02}")
    sub_stim_type_series = csv_data[csv_data["Subject"] == sub_id]["StimType"].tolist()
    gap = 50 if sub == 18 else 25
    sub_stim_type_series = sub_stim_type_series[gap:]

    if len(descriptions) != len(sub_stim_type_series):
        raise ValueError(
            f"Subject {sub}: {len(descriptions)} EEG events but "
            f"{len(sub_stim_type_series)} behavioral trials after offset"
        )
    for i in range(len(descriptions)):
        if int(descriptions[i]) != sub_stim_type_series[i]:
            raise ValueError(
                f"Subject {sub}, trial {i}: EEG marker {descriptions[i]} does not "
                f"match behavioral StimType {sub_stim_type_series[i]}"
            )

    ids = np.arange(0, len(descriptions))
    events = np.array([list(item) for item in list(zip(onsets, durations, ids))], dtype=np.int32)
    epochs = mne.Epochs(raw, events, tmin=EPOCH_TMIN, tmax=EPOCH_TMAX, baseline=BASELINE, preload=True)
    epoch_data = epochs.get_data()

    sub_df = csv_data[csv_data["Subject"] == sub_id]
    acc = sub_df[["Judge1.ACC"]].isin([1])[gap:].squeeze().tolist()
    sub_dict: dict = {"StimType": [], "Marker": [], "RT": [], "StimNo": []}
    for region in REGION_CHANNELS:
        roi_idx = region2index[region]
        roi_mean = epoch_data[:, roi_idx, :].mean(axis=-2)
        valid_data = (np.max(roi_mean, axis=-1) - np.min(roi_mean, axis=-1)) < 30e-6
        valid_data = valid_data & np.array(acc)
        sub_dict[f"{region}_valid_data"] = valid_data.tolist()
        sub_dict[f"{region}_N400"] = epoch_data[:, roi_idx, 350:450].mean(axis=-2).mean(axis=-1).tolist()
        sub_dict[f"{region}_P600"] = epoch_data[:, roi_idx, 450:600].mean(axis=-2).mean(axis=-1).tolist()
        sub_dict[f"{region}_N1"] = epoch_data[:, roi_idx, 250:300].mean(axis=-2).mean(axis=-1).tolist()
        sub_dict[f"{region}_N2"] = epoch_data[:, roi_idx, 300:350].mean(axis=-2).mean(axis=-1).tolist()
        epoch_data_filtered = epoch_data[valid_data, :, :]
        sub_dict[region] = epoch_data_filtered[:, roi_idx, :].mean(axis=-2).mean(axis=0).tolist()

    sub_dict["Marker"] = sub_df[["Marker"]][gap:].squeeze().tolist()
    sub_dict["StimType"] = sub_df[["StimType"]][gap:].squeeze().tolist()
    sub_dict["StimNo"] = sub_df[["StimNo"]][gap:].squeeze().tolist()
    sub_dict["RT"] = sub_df[["Judge1.RT"]][gap:].squeeze().tolist()
    sub_dict["Accuracy"] = acc
    return sub_dict


def main() -> None:
    csv_data = pd.read_excel(_behavior_path())
    u2erp: dict = {}
    for sub in tqdm.tqdm(SUB_LIST):
        u2erp[sub] = preprocess_one(sub, csv_data)

    out = _output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        json.dump(u2erp, fh)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
