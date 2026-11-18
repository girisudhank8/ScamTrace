# ScamTrace — Financial Crime Intelligence & Investigation Platform

> ⚠️ **All data is synthetic and fictional. No real persons, accounts, or transactions are implicated.**  
> 📋 **Developer Documentation & Phase Checklist:** See [DEVELOPMENT_CHECKLIST.md](DEVELOPMENT_CHECKLIST.md) for architecture, schemas, full developer checklists, and phase roadmap.

---

## Overview

**ScamTrace** is a hackathon-ready prototype for **PS-06: Integrated Financial Investigation & Anti-Money Mule Platform**.

It ingests bank statements and UPI transaction logs, normalizes them, reconstructs multi-hop money trails, detects suspicious mule accounts, correlates victim complaints, visualizes financial networks, and generates forensic PDF reports — all locally, without any paid APIs.

---

## Features

| Module | Capability |
|--------|-----------|
| 📥 Data Ingestion | CSV, Excel, PDF upload; column auto-mapping; dedup; validation |
| 🔍 Money Trail | BFS/DFS multi-hop tracing; date/amount filters; PyVis graph |
| 🎯 Mule Detection | Explainable risk scoring; Isolation Forest; transparent factors |
| 🔗 Cross-Complaint | Shared account detection; correlation graph; timeline |
| 🌐 Network Intelligence | Full graph with centrality, PageRank, community detection |
| 📋 Forensic Reports | ReportLab PDF with evidence hashes, trails, risk explanations |
| 🔐 Evidence Integrity | SHA-256 hashing, chain-of-custody, tamper verification |

---

## Tech Stack

- **Frontend:** Streamlit
- **Data:** Pandas, NumPy
- **Graph:** NetworkX, PyVis
- **Charts:** Plotly
- **ML:** Scikit-learn (Isolation Forest)
- **DB:** SQLite + SQLAlchemy
- **PDF:** ReportLab
- **Hashing:** hashlib SHA-256
- **Validation:** Pydantic-compatible, pytest

---

## Installation

```bash
# 1. Clone / navigate to project
cd G:\CYS\5\scamtrace

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic data (already included)
python generate_data.py

# 4. Launch the app
streamlit run app.py
```

---

## Running the App

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## Demo Workflow

1. **Overview** → Load Demo Investigation (button)
2. **Money Trail** → Select `ACC_V001` → Trace Outgoing (depth 5) → see 4-hop chain
3. **Mule Detection** → Run Detection → inspect `ACC_M001` risk explanation
4. **Cross-Complaint** → Select CMP001 + CMP002 → Correlate → see shared `ACC_M007`
5. **Network Intelligence** → Render Graph (Flagged Only) → inspect communities
6. **Evidence Integrity** → Register synthetic CSV → verify hash
7. **Forensic Reports** → Select complaints → Generate PDF → Download

---

## Project Structure

```
scamtrace/
├── app.py                      # Streamlit main entry point
├── config.py                   # Configuration & constants
├── generate_data.py            # Synthetic dataset generator
├── requirements.txt
├── README.md
├── .env.example
├── data/
│   ├── synthetic_accounts.csv       (120 accounts)
│   ├── synthetic_transactions.csv   (600 transactions)
│   ├── synthetic_complaints.csv     (5 complaints)
│   └── README_DATA.md
├── modules/
│   ├── database.py             # SQLite + SQLAlchemy ORM
│   ├── ingestion.py            # CSV/Excel/PDF ingest
│   ├── preprocessing.py        # Normalization & feature engineering
│   ├── graph_analytics.py      # NetworkX BFS/DFS, cycles, communities
│   ├── fraud_detection.py      # Explainable risk scoring + Isolation Forest
│   ├── evidence.py             # SHA-256 chain-of-custody
│   └── reports.py              # ReportLab PDF generation
├── pages/
│   ├── 01_Overview.py
│   ├── 02_Data_Ingestion.py
│   ├── 03_Money_Trail.py
│   ├── 04_Mule_Detection.py
│   ├── 05_Cross_Complaint.py
│   ├── 06_Network_Intelligence.py
│   ├── 07_Forensic_Reports.py
│   └── 08_Evidence_Integrity.py
├── tests/
│   ├── test_graph.py
│   ├── test_fraud.py
│   ├── test_evidence.py
│   └── test_ingestion.py
├── assets/
│   └── style.css               # Dark-theme CSS
├── uploads/                    # Evidence file storage (auto-created)
└── reports_output/             # Generated PDFs (auto-created)
```

---

## Running Tests

```bash
cd G:\CYS\5\scamtrace
pytest tests/ -v
```

---

## Key Investigation Scenarios (Synthetic)

| Scenario | Victim | Chain | Shared Node |
|----------|--------|-------|-------------|
| CMP001 | ACC_V001 | V001→M001→M003→M007→L050 | ACC_M007 |
| CMP002 | ACC_V002 | V002→M002→M004→M007→L060 | ACC_M007 |
| CMP003 | ACC_V003 | V003→M005→{M008,M009}→M010→L070 | ACC_M010 |
| CMP004 | ACC_V004 | V004→M006→M009→L090 | ACC_M009 |
| CMP005 | ACC_V005 | V005→M001→M002→L095 | ACC_M001, ACC_M002 |
| Circular | — | M003↔M006 (cycle) | — |

---

## Disclaimer

> This is a **demonstration prototype** built on entirely **synthetic data**. It does not represent real financial records, transactions, or persons. Risk scores are heuristic behavioral indicators and do not constitute evidence of criminal activity. All results require human investigation before any conclusions are drawn.

---

*Built for a national-level cybersecurity hackathon. ScamTrace v1.0.0*
