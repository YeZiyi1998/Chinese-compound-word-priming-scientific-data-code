# Native-data audit findings (2026-08-23)

These values come from a metadata-only run across the native `合作_nc` source.
They describe available files, not the final ethics-approved public cohort.

| Experiment | Native participants represented | Recordings | Linked trials | Correct trials | RT <300 ms | RT <500 ms | RT <800 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1, masked 50 ms | 30 | 30 | 16,500 | 15,958 | 70 | 1,051 | 12,902 |
| 2, unmasked 50 ms | 37 | 38 | 20,346 | 19,610 | 88 | 1,325 | 16,157 |
| 3, unmasked 200 ms | 30 | 30 | 16,500 | 15,872 | 57 | 873 | 12,731 |
| Total | 97 | 98 | 53,346 | 51,440 | 215 | 3,249 | 41,790 |

Important reconciliation items:

- The manuscript cites analyzed samples of 30, 27, and 28, but the native
  source contains linked data for 30, 37, and 30 participant codes. Exclusion
  identities and reasons for Experiments 2 and 3 must be supplied by the author
  team before defining the public/raw and derivative cohorts.
- Experiment 2 participant 31 has two native recordings (440 + 110 trials).
  The release code preserves these truthfully as `run-01` and `run-02`; the
  manuscript's statement that every participant has one recording must change
  unless a documented lossless concatenation policy is approved.
- Experiment 2 participant 2 has four missing behavioral rows in the preserved
  mapping, yielding 546 rather than 550 linked trials. The correction is
  recorded in `native_to_bids_mapping.tsv`.
- Native headers report 63 recorded channels: 61 channels classified as EEG by
  the current code (including the two mastoids) and two EOG channels. The
  manuscript's “62 scalp electrodes” statement requires author/hardware
  reconciliation rather than automatic restatement.
- The median delay between behavioral RT and the EEG response trigger is
  63–65 ms across participants. After participant-level median calibration,
  213/53,346 trials differ by more than 25 ms, with some ~1,987-ms outliers.
  These must remain flagged and investigated; raw and calibrated timing columns
  are both retained.
- Raw participant counts are not evidence that public release is authorized.
  Every generated participant row remains marked
  `pending_ethics_authorization` until written authorization is confirmed.
