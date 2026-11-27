# Aabo AI — read a link before you trust it

A URL-only phishing classifier: it reads the **structure of an address** and returns a verdict
with the evidence behind it, without ever fetching the page.

**Live demo:** https://aabo-ai.vercel.app
(Yoruba *ààbò*, protection.)

Final-year project — AI-Powered Phishing Detection and URL Classification Tool, Department of
Computer Science, National Open University of Nigeria, November 2026. This folder is the
complete working system behind the project document; the chapters are the source of that
document, so the code reproduced in its appendices is the code in this repository.

## What it does

Sixteen lexical and structural features are computed from the URL string alone — length,
hostname depth, IP-literal host, `@` symbol, `https`, hyphen and digit density, suspicious
tokens, suspicious TLD, encoded characters, brand-in-subdomain — and scored by a Random Forest
of 200 trees. Median response is about 15 ms.

Every result is one of three states:

| state | meaning |
|---|---|
| **Phishing** | the model accuses the address and nothing contradicts it |
| **Legitimate** | the model clears the address |
| **Unverified** | the model accuses it, but a second reading does not support the accusation — both scores are shown, with the reason |

`Unverified` never silently becomes `Legitimate`: a curated list may only downgrade an
accusation, never clear one, and domain identity is never a classifier feature.

## What is here

| File | Purpose |
|---|---|
| `app.py` | FastAPI service: the interface, `/api/classify`, `/api/history`, `/api/metrics` |
| `app/index.html` | The browser interface (single file, no framework, no CDN) |
| `train.py` | The 16 features, plus the first-generation training run |
| `retrain.py` | The corrected training run — the model that is deployed |
| `domain_utils.py` | Host parsing, allow-list tiers, likely-restricted registries |
| `domain_first.py`, `domain_first_cost.py` | The field tests behind Section 4.6.8 |
| `generalise.py`, `generalise_fullurl.py` | Cross-source generalisation tests |
| `ablation.py` | Ablation study: retrains without `path_length` and re-tests everything |
| `diagrams.py`, `figs_*.py` | Draws the diagrams and result charts used in the document |
| `build_project.py` | Builds the Word document from `ch1.md … ch6.md` |
| `functional_tests.py` | The twelve requirement tests, run against the live service |
| `artifacts/` | `model_selected.joblib`, metrics JSON, allow-lists, the scan log |
| `vercel.json`, `requirements.txt` | Deployment configuration and runtime dependencies |

The chapter sources behind the written report, the built `.docx`, the training dataset and the
local virtualenv are deliberately **not** published here.

## Run the application

```bash
cd Stella_Project
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt      # runtime only (~135 MB)
.venv/bin/python -m uvicorn app:app --port 8077
```

Then open http://localhost:8077

`artifacts/model_selected.joblib` (93 MB) is committed because the service cannot start
without it. Research and document-build dependencies are kept separate:

```bash
.venv/bin/pip install -r requirements-research.txt   # pandas, matplotlib, python-docx
```

## Rebuild the document

```bash
.venv/bin/python build_project.py                    # writes ../Stella_Project_DRAFT.docx
```

`build_project.py` renders the chapter markdown into the formatted document. The chapter sources
and the generated figures are not published in this repository, so this step runs from a working
copy; the figures are produced by `diagrams.py` and `figs_*.py`, and the chapters reference them by
absolute path in their `{{FIG: caption || PNG::/path}}` markers.

## Reproduce the results

```bash
.venv/bin/python train.py               # metrics.json, feature_importance.csv, confusion matrices
.venv/bin/python retrain.py             # the corrected dataset and the deployed model
.venv/bin/python generalise.py          # generalisation.json
.venv/bin/python ablation.py            # ablation.json
.venv/bin/python domain_first.py        # domain_first.json
.venv/bin/python functional_tests.py    # functional_tests.json (service must be running)
```

## Data files not included

Large inputs are excluded to keep the repository small. Re-download into `data/`:

- `PhiUSIIL_Phishing_URL_Dataset.csv` — https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
- `top-1m.csv` — https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip

Blocklist samples used for evaluation come from Phishing.Database and the Phishing Army list.
The Phishing Army list is also bundled at `artifacts/blocklist_hostile.txt` — 112,433
registrable domains after public-suffix normalisation — and is consulted at scan time as
`build_hostile_blocklist.py` describes: a listed domain's accusation is never weakened by the
domain-first rule, but the list never creates an accusation and never clears one. It is not a
study tier and is excluded from the reputation-layer counts.

## The finding (the project's main result)

Trained on PhiUSIIL alone, the model reaches **99.59% accuracy** on held-out records and
**66.6%** on 1,000 unseen addresses from independent sources. The dataset, not the model, was
at fault: every legitimate record in PhiUSIIL is a single URL shape — an HTTPS address
beginning with `www` and carrying no path — while 59.9% of phishing records carry one, so the
classifier had learned the *template of the legitimate class* rather than the appearance of an
attack.

Corrected by extending the legitimate class with 17,705 rows harvested from 194 domains and
generated over 2,024 well-known domains, the deployed model reaches **88.44%** accuracy on a
7,368-address field test and **95.48%** with the reputation layer, at a measured cost of
in-dataset accuracy falling to 95.73% and hostile recall to 81.10%.

The **domain-first rule** is the study's most honest result. Requiring an accusation to be
supported by the main domain alone removed **529 of 569** false accusations of legitimate
addresses carrying a path (41.59% → 3.00%) — but weakened **36.5%** of hostile accusations of
that same shape. The two effects are the same size, and that symmetry is the point: once the
path is what drives an accusation, it says almost nothing about whether the address is
dangerous. Such cases are shown as `unverified` rather than as malicious.

## Deployment

Deployed on Vercel's free tier; pushing to `main` redeploys. `vercel.json` pins the runtime and
keeps the local virtualenv and dataset out of the function bundle, and `app.py` is the
auto-detected FastAPI entrypoint.

Two limits stated plainly: the scan log lives in `/tmp` because a serverless filesystem is
read-only apart from that, so **log history resets when the instance recycles**; and the API is
public and unauthenticated. This is a demonstration system, not a production service.

## Licence and attribution

PhiUSIIL Phishing URL Dataset (Prasad & Chandra, 2024), distributed via the UCI Machine
Learning Repository, used under its original licence.

Phishing Army blocklist (https://phishing.army/), bundled at `artifacts/blocklist_hostile.txt`
for the hosted demonstration. Used for non-commercial purposes under the terms published at
https://phishing.army/license/; the source is named in `artifacts/blocklist_report.json` and the
list is redistributed unmodified in substance, reduced to registrable domains.
