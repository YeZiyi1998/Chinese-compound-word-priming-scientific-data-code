# Scientific Data release workflow

The workflow implements the code-addressable claims in the Data Descriptor.
It does not replace ethics approval, public-release authorization, missing
acquisition metadata, author decisions, or repository/DOI registration.

## 1. Build a review snapshot

```bash
python -m src.release.build \
  --source-root /path/to/native/source \
  --output-root /path/to/release
```

The builder copies the binary EEG byte-for-byte, rewrites BrainVision file
references, removes the recording timestamp from the copied marker header,
and creates BIDS names, participants, channels, rich trial events, stimuli,
native-to-BIDS mapping, a trial-resolved derivative, and a data dictionary.
The native source remains unchanged.

Use `--no-copy-eeg` only for a quick metadata audit. Use `--limit 1` to test one
participant from each experiment.

## 2. Run internal and official BIDS validation

```bash
python -m src.release.validate --root /path/to/release --tolerance-ms 25
npx bids-validator /path/to/release \
  --json > /path/to/release/derivatives/validation/bids-validator.json
```

The internal validator checks root files, participant/event cardinality,
required trial fields, unique keys, onset order, RT reconstruction after the
participant-specific median response-trigger offset, and counts
responses occurring before 300/500/800 ms. The BIDS Validator is authoritative
for specification compliance. Record its exact version with the report.

## 3. Generate signal QC

```bash
python -m src.release.qc --root /path/to/release
```

This produces recording/channel metrics and a summary figure. Metrics include
sampling rate, channel/sample counts, duration, non-finite samples, variance,
peak-to-peak amplitude, flat-channel flags, EOG correlation, and 50-Hz power
ratio. Review thresholds must be approved and documented before converting
metric values into noisy-channel or exclusion decisions.

## 4. Freeze and verify

```bash
python -m src.release.manifest --root /path/to/release
python -m src.release.manifest --root /path/to/release \
  --verify /path/to/release/derivatives/validation/release_manifest.tsv
```

Generate the manifest only after every report and derivative is final. Any
subsequent correction must create a new version rather than overwrite the
cited snapshot.

## Author-supplied blockers before public release

- Ethics/consent authorization for public de-identified human EEG data.
- Final inclusion/exclusion inventory and reasons, especially Experiment 2.
- Age/sex resolution permitted for release and a full identifier/header audit.
- Online reference, ground, amplifier range/resolution, trigger interface,
  coordinate source, monitor/presentation software, response keys/device.
- Exact published-analysis artifact/ocular/bad-channel parameters.
- Approved harmonized preprocessing policy and noisy-channel thresholds.
- Final authors, affiliations, CRediT roles, funding, licenses, accession/DOI.

Until these are supplied, generated metadata deliberately uses explicit
`PENDING_*` values and `release_status=pending_ethics_authorization`.
