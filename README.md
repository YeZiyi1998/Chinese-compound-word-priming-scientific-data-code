# Trial-resolved Chinese lexical-priming EEG: preprocessing code

Code accompanying the *Scientific Data* Data Descriptor for three Chinese
lexical-decision EEG experiments: masked 50-ms primes, unmasked 50-ms primes,
and unmasked 200-ms primes.

This repository has one deliberately narrow role: convert the preserved
BrainVision recordings and behavioral workbooks into the trial-resolved JSON
derivatives used by downstream analyses. The raw EEG, behavioral data,
EEG-BIDS conversion/validation workflow, quality-control records, and frozen
data release are not included in this source snapshot and must be deposited
separately before submission.

## Repository layout

```text
src/preprocessing/       experiment-specific preprocessing scripts
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

Place the data as described in `data/README.md`, then run from the repository
root:

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

Important: these scripts preserve the analysis pipeline represented in the
working materials. They do not yet constitute the complete EEG-BIDS release
workflow claimed by the Data Descriptor. BIDS conversion, validator output,
checksums, provenance, a data dictionary, and repository-derived QC summaries
must be added when the frozen data snapshot exists.

## Citation and license

Citation metadata and an open-source license should be added after the author
team confirms the final manuscript record and reuse terms.
