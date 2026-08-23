# Trial-resolved Chinese lexical-priming EEG: preprocessing code

Code accompanying the *Scientific Data* Data Descriptor for three Chinese
lexical-decision EEG experiments: masked 50-ms primes, unmasked 50-ms primes,
and unmasked 200-ms primes.

This repository builds and audits the multi-experiment EEG-BIDS release
described in the manuscript. It also retains the original experiment-specific
preprocessing scripts for historical/JML derivatives.

## Repository layout

```text
src/preprocessing/       experiment-specific preprocessing scripts
src/release/             BIDS build, validation, QC and checksum tools
data/README.md           expected local input/output layout
requirements.txt         Python dependencies
```

## Setup

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

For the complete release pipeline, follow `WORKFLOW.md`. Place the data as
described in `data/README.md`. The historical analysis derivatives can be
generated from the repository root with:

```bash
python -m src.preprocessing.preprocess_exp1
python -m src.preprocessing.preprocess_exp2
python -m src.preprocessing.preprocess_exp3
```

Each script applies a 0.5–30 Hz filter, average-mastoid reference, the
experiment-specific target-locked epoch/baseline, a 30 µV peak-to-peak ROI
criterion, and exclusion of incorrect lexical decisions. It writes
`data/results/expN_u2erp.json` with trial identifiers, RT, accuracy, validity
flags, ROI window means, and averaged waveforms.

The release code covers BIDS construction, event/behavior linking, provenance
mapping, data dictionary generation, internal validation, EEG QC, overlap
counts, and SHA-256 manifests. Author-dependent blockers are enumerated in
`WORKFLOW.md`; the software does not fabricate unavailable ethics, acquisition,
demographic, licensing, authorship, or DOI information.

## Citation and license

Citation metadata and an open-source license should be added after the author
team confirms the final manuscript record and reuse terms.
