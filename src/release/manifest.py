"""Generate and verify the immutable release checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def create(root: Path) -> Path:
    output = root / "derivatives" / "validation" / "release_manifest.tsv"
    files = [p for p in root.rglob("*") if p.is_file() and p != output]
    rows = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size,
             "sha256": digest(p)} for p in sorted(files)]
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, sep="\t", index=False)
    return output


def verify(root: Path, manifest: Path) -> list[str]:
    failures = []
    for row in pd.read_csv(manifest, sep="\t").itertuples():
        path = root / row.path
        if not path.is_file() or path.stat().st_size != row.bytes or digest(path) != row.sha256:
            failures.append(row.path)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        failures = verify(args.root, args.verify)
        print("\n".join(failures) if failures else "All checksums match.")
        raise SystemExit(bool(failures))
    print(create(args.root))


if __name__ == "__main__":
    main()
