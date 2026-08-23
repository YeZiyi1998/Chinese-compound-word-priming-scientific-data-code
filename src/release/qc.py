"""Participant/channel EEG quality metrics and release-level QC figure."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
from scipy.signal import welch


def recording_metrics(vhdr: Path) -> tuple[list[dict], dict]:
    raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
    # Uniformly sample at most 120 s across the record to bound memory while
    # retaining all channels and the full recording span.
    step = max(1, int(raw.n_times / (raw.info["sfreq"] * 120)))
    data = raw.get_data()[:, ::step] * 1e6
    effective_sfreq = raw.info["sfreq"] / step
    rows = []
    eog_idx = [i for i, n in enumerate(raw.ch_names) if n in {"HEOG", "VEOG"}]
    eog_mean = data[eog_idx].mean(axis=0) if eog_idx else np.zeros(data.shape[1])
    for index, name in enumerate(raw.ch_names):
        signal = data[index]
        freqs, power = welch(signal, fs=effective_sfreq, nperseg=min(2048, len(signal)))
        line = power[(freqs >= 49) & (freqs <= 51)].sum()
        broadband = power[(freqs >= 1) & (freqs <= min(100, effective_sfreq / 2))].sum()
        corr = np.corrcoef(signal, eog_mean)[0, 1] if eog_idx and index not in eog_idx else np.nan
        rows.append({"channel": name, "variance_uv2": np.var(signal),
                     "peak_to_peak_uv": np.ptp(signal), "line_noise_ratio": line / broadband if broadband else np.nan,
                     "eog_correlation": corr, "flat": bool(np.ptp(signal) < 0.5),
                     "nonfinite_samples": int((~np.isfinite(signal)).sum())})
    return rows, {"sampling_frequency": raw.info["sfreq"], "n_channels": len(raw.ch_names),
                  "n_samples": raw.n_times, "duration_s": raw.n_times / raw.info["sfreq"]}


def run(root: Path) -> None:
    channel_rows, recording_rows = [], []
    for vhdr in sorted(root.glob("sub-*/eeg/*_eeg.vhdr")):
        participant = vhdr.parts[-3]
        rows, summary = recording_metrics(vhdr)
        channel_rows.extend([{"participant_id": participant, **r} for r in rows])
        recording_rows.append({"participant_id": participant, **summary,
                               "flat_channels": sum(r["flat"] for r in rows),
                               "nonfinite_samples": sum(r["nonfinite_samples"] for r in rows)})
    out = root / "derivatives" / "quality-control"
    out.mkdir(parents=True, exist_ok=True)
    channels = pd.DataFrame(channel_rows)
    recordings = pd.DataFrame(recording_rows)
    channels.to_csv(out / "eeg_channel_metrics.tsv", sep="\t", index=False)
    recordings.to_csv(out / "eeg_recording_metrics.tsv", sep="\t", index=False)
    if not recordings.empty:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].hist(recordings["duration_s"] / 60, bins=20)
        axes[0].set(xlabel="Recording duration (min)", ylabel="Participants")
        channels.boxplot(column="line_noise_ratio", by="participant_id", ax=axes[1], rot=90, grid=False)
        axes[1].set(xlabel="Participant", ylabel="50-Hz / broadband power", title="")
        fig.suptitle("Release quality-control summary")
        fig.tight_layout()
        fig.savefig(out / "quality_control_summary.png", dpi=200)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    run(args.root.resolve())


if __name__ == "__main__":
    main()
