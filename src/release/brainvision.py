"""Minimal, lossless BrainVision parsing and BIDS-safe copying."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, str(path))


def header_metadata(vhdr: Path) -> dict:
    text = read_text(vhdr)
    def field(name: str) -> str:
        match = re.search(rf"(?mi)^{re.escape(name)}=(.+)$", text)
        if not match:
            raise ValueError(f"{vhdr}: missing {name}")
        return match.group(1).strip()
    channels = []
    for match in re.finditer(r"(?mi)^Ch(\d+)=(.*)$", text):
        parts = match.group(2).split(",")
        channels.append({"index": int(match.group(1)), "name": parts[0],
                         "unit": parts[3] if len(parts) > 3 else "n/a"})
    interval_us = float(field("SamplingInterval"))
    return {"data_file": field("DataFile"), "marker_file": field("MarkerFile"),
            "n_channels": int(field("NumberOfChannels")),
            "sampling_frequency": 1_000_000.0 / interval_us,
            "channels": channels, "text": text}


def markers(vmrk: Path) -> list[dict]:
    rows = []
    for line in read_text(vmrk).splitlines():
        match = re.match(r"Mk(\d+)=(.*)", line)
        if not match:
            continue
        parts = match.group(2).split(",")
        if len(parts) < 5:
            continue
        rows.append({"marker_index": int(match.group(1)), "type": parts[0],
                     "description": parts[1].strip(), "sample": int(parts[2]),
                     "size_samples": int(parts[3]), "channel": int(parts[4])})
    return rows


def _replace_field(text: str, name: str, value: str) -> str:
    return re.sub(rf"(?mi)^{re.escape(name)}=.*$", f"{name}={value}", text, count=1)


def copy_brainvision(vhdr: Path, destination_stem: Path) -> dict:
    """Copy the binary unchanged and rewrite only inter-file references."""
    meta = header_metadata(vhdr)
    source_eeg = vhdr.parent / meta["data_file"]
    source_vmrk = vhdr.parent / meta["marker_file"]
    for path in (source_eeg, source_vmrk):
        if not path.is_file():
            raise FileNotFoundError(path)
    destination_stem.parent.mkdir(parents=True, exist_ok=True)
    out_eeg = destination_stem.with_suffix(".eeg")
    out_vmrk = destination_stem.with_suffix(".vmrk")
    out_vhdr = destination_stem.with_suffix(".vhdr")
    shutil.copyfile(source_eeg, out_eeg)
    vhdr_text = _replace_field(meta["text"], "DataFile", out_eeg.name)
    vhdr_text = _replace_field(vhdr_text, "MarkerFile", out_vmrk.name)
    out_vhdr.write_text(vhdr_text, encoding="utf-8", newline="\n")
    marker_text = _replace_field(read_text(source_vmrk), "DataFile", out_eeg.name)
    # Remove acquisition timestamp from New Segment marker for de-identification.
    marker_text = re.sub(r"(?m)^(Mk\d+=New Segment,[^\r\n]*?,\d+,\d+,\d+),[^\r\n]*$", r"\1", marker_text)
    out_vmrk.write_text(marker_text, encoding="utf-8", newline="\n")
    samples = source_eeg.stat().st_size // (meta["n_channels"] * 2)
    return {**meta, "n_samples": samples, "duration_s": samples / meta["sampling_frequency"],
            "source_vmrk": source_vmrk, "output_files": [out_vhdr, out_vmrk, out_eeg]}

