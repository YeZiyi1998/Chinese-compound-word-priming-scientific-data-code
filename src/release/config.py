"""Frozen experiment metadata and documented native-data corrections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Experiment:
    id: int
    acquisition: str
    masking_context: str
    prime_duration_ms: int
    preprime_display: str
    behavior_file: str
    eeg_dir: str
    native_prefix: str
    subject_ids: tuple[int, ...]

    def native_eeg_id(self, subject: int) -> int:
        if self.id == 2:
            return {3: 4, 4: 3, 12: 13, 13: 12}.get(subject, subject)
        return subject

    def behavior_id(self, subject: int) -> int:
        return 300 + subject if self.id == 3 else subject

    def practice_rows(self, subject: int) -> int:
        if self.id == 1:
            return 50 if subject == 12 else 25
        if self.id == 2:
            return 0 if subject == 10 else 25
        return 50 if subject == 18 else 25

    def source_stem(self, subject: int) -> str:
        value = self.native_eeg_id(subject)
        return f"{self.native_prefix}{value:02d}"

    def participant(self, subject: int) -> str:
        return f"exp{self.id}p{subject:02d}"

    def recording_stems(self, subject: int) -> tuple[str, ...]:
        primary = self.source_stem(subject)
        return (primary, f"subject{subject:02d}-2") if self.id == 2 and subject == 31 else (primary,)


EXPERIMENTS = {
    1: Experiment(1, "masked50", "masked", 50, "forward_pattern_mask",
                  "实验一行为数据-mask&SOA=50ms.xlsx", "实验1脑电数据", "sub",
                  tuple(range(1, 31))),
    2: Experiment(2, "unmasked50", "unmasked", 50, "fixation_cross",
                  "实验二行为数据-unmask&SOA=50ms.xlsx", "实验2脑电数据", "subject",
                  tuple(i for i in range(1, 39) if i != 35)),
    3: Experiment(3, "unmasked200", "unmasked", 200, "fixation_cross",
                  "实验三行为数据-unmask&SOA=200ms.xlsx", "实验3脑电数据", "3EXP",
                  tuple(range(1, 31))),
}


def source_paths(source_root: Path, exp: Experiment, subject: int) -> tuple[Path, Path]:
    base = source_root / f"exp{exp.id}" / exp.eeg_dir / exp.source_stem(subject)
    return base.with_suffix(".vhdr"), source_root / f"exp{exp.id}" / exp.behavior_file


def recording_paths(source_root: Path, exp: Experiment, subject: int) -> tuple[Path, ...]:
    folder = source_root / f"exp{exp.id}" / exp.eeg_dir
    return tuple((folder / stem).with_suffix(".vhdr") for stem in exp.recording_stems(subject))
