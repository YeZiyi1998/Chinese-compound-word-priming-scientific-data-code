# Local data layout

Data are intentionally excluded from Git. Create the following directories or
symbolic links locally:

```text
data/
├── exp1/
│   ├── 实验一行为数据-mask&SOA=50ms.xlsx
│   └── 实验1脑电数据/sub??.vhdr (+ .eeg/.vmrk companions)
├── exp2/
│   ├── 实验二行为数据-unmask&SOA=50ms.xlsx
│   └── 实验2脑电数据/subject??.vhdr (+ companions)
├── exp3/
│   ├── 实验三行为数据-unmask&SOA=200ms.xlsx
│   └── 实验3脑电数据/3EXP??.vhdr (+ companions)
└── results/                       generated expN_u2erp.json files
```

Do not commit raw or identifiable participant data. The public data archive
should use the approved de-identification and EEG-BIDS release procedure.
