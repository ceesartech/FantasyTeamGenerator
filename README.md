# TeamGenarator – AWS-Native, Multi-Week, Captaincy-Aware

[![GitHub Stars](https://img.shields.io/github/stars/ceesartech/FantasyTeamGenerator)](https://github.com/ceesartech/FantasyTeamGenerator)
[![AWS](https://img.shields.io/badge/AWS-serverless-orange.svg)](https://aws.amazon.com)
[![Infra-as-Code](https://img.shields.io/badge/IaC-Terraform-623CE4.svg)](https://www.terraform.io/)
[![GitHub Languages](https://img.shields.io/github/languages/top/ceesartech/FantasyTeamGenerator)](https://github.com/ceesartech/FantasyTeamGenerator)

A production-ready **Fantasy Premier League squad optimizer** that ingests official FPL data, builds features, predicts expected points (xPts), and solves the squad-building problem under all official constraints. It supports **multi-week horizons with discounting**, **automatic captain selection**, **club/budget/position constraints**, and **user constraints** (must include/exclude, and **optimize around specific player names**). Delivered as an **AWS-native** system (Lambda, Step Functions, SageMaker, S3, DynamoDB, API Gateway, EventBridge, SNS) with a small React frontend.

Repository: **https://github.com/ceesartech/FantasyTeamGenerator**

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Quickstart (TL;DR)](#quickstart-tldr)
- [Configuration](#configuration)
- [Deploy Infrastructure](#deploy-infrastructure)
- [Build & Publish Lambdas](#build--publish-lambdas)
- [Frontend](#frontend)
- [Data Contracts](#data-contracts)
- [API](#api)
- [Optimizer Details](#optimizer-details)
- [Pipelines](#pipelines)
- [Security & Compliance](#security--compliance)
- [Cost Notes](#cost-notes)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **End-to-end pipeline**: ingest → feature build → model scoring → ILP optimization → persist → notify.
- **Multi-week horizon** with **discounted expected points**.
- **Automatic captaincy** per week (one captain per GW; doubles xPts).
- **All official FPL constraints**:
  - 15 players: `2 GK, 5 DEF, 5 MID, 3 FWD`
  - ≤3 players per club
  - Budget ≤ team value (default £100.0m)
- **User constraints**:
  - Must include / exclude by `player_id`
  - **Optimize around player names** (e.g., `["Salah"]`): forces ≥1 matching selection
  - (Optional) restrict captain to positions (e.g., `["MID","FWD"]`)
- **Transfer advice**: given your current 15, computes ins/outs, free-transfer usage, and points hit penalty.
- **API first**: FastAPI on Lambda (API Gateway HTTP API).
- **Infra as Code**: Terraform.
- **Observability**: CloudWatch logs/alarms; SNS alerts.
- **Frontend**: minimal React “What-If” UI.

---

## Architecture

```mermaid
graph TD
  EB[EventBridge Schedules] --> SFN[Step Functions Scoring Pipeline]
  API[API Gateway] --> LAPI[Lambda: FastAPI]
  LAPI --> DDB[(DynamoDB: squads)]
  SFN --> LING[Lambda: Ingest FPL]
  LING --> S3R[(S3: raw)]
  SFN --> LFEAT[Lambda/SageMaker Processing: Features]
  LFEAT --> S3Ref[(S3: refined)]
  SFN --> LBINF[Lambda: Batch Inference Launcher]
  LBINF --> SM[Amazon SageMaker Batch Transform]
  SM --> S3Ref
  SFN --> LOPT[Lambda (container): Optimizer]
  LOPT --> DDB
  SFN --> SNS[SNS: Alerts]
  UI[React (Vite)] -->|fetch| API
```
_____________________________________________________________________

## Repository Structure
```angular2html
fpl-optimizer/
├── backend/
│   ├── optimizer/                  # Python package (OOP ILP core)
│   │   ├── pyproject.toml
│   │   └── src/fpl_opt/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── domain.py
│   │       ├── data_access.py
│   │       ├── optimizer.py
│   │       ├── captaincy.py
│   │       ├── advice.py
│   │       ├── exceptions.py
│   │       └── util.py
│   ├── lambdas/
│   │   ├── ingest_fpl/
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   ├── optimize_squad/         # OR-Tools ILP (container)
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── app.py
│   │   ├── api/                    # FastAPI on Lambda (container)
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── app.py
│   │   ├── sm_training_launcher/
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   └── sm_batch_inference/
│   │       ├── handler.py
│   │       └── requirements.txt
│   └── sagemaker/
│       ├── processing/
│       │   └── feature_and_join.py
│       └── training/
│           ├── train_minutes_xgb.py
│           └── train_xpts_xgb.py
├── infra/
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── iam.tf
│       ├── sagemaker.tf
│       ├── stepfunctions.tf
│       ├── apigw.tf
│       ├── events.tf
│       └── locals.tf
├── pipelines/
│   └── state_machines/
│       ├── scoring_pipeline_v2.asl.json
│       └── training_pipeline_v2.asl.json
└── frontend/
    └── webapp/
        ├── index.html
        ├── package.json
        ├── vite.config.js
        └── src/
            ├── main.jsx
            └── App.jsx
```
_____________________________________________________________________

## Prerequisites
* AWS Account with admin-level or project-scoped permissions
* AWS CLI v2 configured (aws configure)
* Terraform ≥ 1.7
* Docker (build/push Lambda container images)
* Python 3.12 (for packaging the zip Lambda locally)
* Node 18+ (for frontend)
_____________________________________________________________________


## Quickstart (TL;DR)
```shell
# 1) Build & push container images (update <acct> + region)
cd backend/lambdas/optimize_squad
docker build -t fpl-optimizer-optimize .
aws ecr create-repository --repository-name fpl-optimizer-optimize || true
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <acct>.dkr.ecr.us-east-1.amazonaws.com
docker tag fpl-optimizer-optimize:latest <acct>.dkr.ecr.us-east-1.amazonaws.com/fpl-optimizer-optimize:latest
docker push <acct>.dkr.ecr.us-east-1.amazonaws.com/fpl-optimizer-optimize:latest

cd ../api
docker build -t fpl-optimizer-api .
aws ecr create-repository --repository-name fpl-optimizer-api || true
docker tag fpl-optimizer-api:latest <acct>.dkr.ecr.us-east-1.amazonaws.com/fpl-optimizer-api:latest
docker push <acct>.dkr.ecr.us-east-1.amazonaws.com/fpl-optimizer-api:latest

# 2) Package zip Lambda (ingest)
cd ../../ingest_fpl
pip install -r requirements.txt -t .
zip -r ingest_fpl.zip .
# Ensure Terraform references this zip path

# 3) Terraform deploy
cd ../../../infra/terraform
terraform init
terraform apply -var="account_suffix=dev001" -auto-approve

# 4) Frontend (Vite React)
cd ../../frontend/webapp
echo "VITE_API_BASE=$(terraform -chdir=../../infra/terraform output -raw api_endpoint)" > .env
npm i
npm run build
# Deploy build/ via S3+CloudFront, Amplify, Netlify, etc.
```

> After your first scoring run (or a manual /optimize call), fetch the saved squad via:
GET /squad?gameweek=2&variant=user_specified
> _____________________________________________________________________

## Configuration
### SSM Parameter
* `/fpl-team-generator/fpl_base_url` → defaults to https://fantasy.premierleague.com/api

### S3 Buckets (Terraform Managed)
* <project>-raw-<suffix> – raw FPL JSON
* <project>-refined-<suffix> – features/xPts parquet
* <project>-batch-<suffix> – SageMaker Batch Transform outputs

### DynamoDB
* Table: <project>-squads-<suffix>
* Key schema: pk="GW#<n>", sk="variant#<name>"

### Lambda Environment Variables
* DDB_TABLE (optimizer + API)
* RAW_BUCKET, FPL_BASE_URL_PARAM (ingest)
* XPTS_MODEL_PACKAGE_ARN, BATCH_OUTPUT_S3 (batch inference)
* SAGEMAKER_EXEC_ROLE_ARN, SM_ARTIFACTS_S3, XPTS_MODEL_PKG_GROUP (training launcher)
* BUDGET_DEFAULT (optional default for optimizer)

### Eventbridge
* Daily schedule triggers the scoring pipeline (time would be in UTC, so it is not time-zone dependent)
_____________________________________________________________________


## Deploy Infrastructure
From `infrastructure/terraform`:
```shell
terraform init
terraform apply -var="account_suffix=dev001"
```

### Outputs
* `api_endpoint` - paste into frontend `.env` as `VITE_API_BASE`.
* `*_bucket` names, DynamoDB table name.
_____________________________________________________________________


## Build & Publish Lambdas

### Container Lambdas
* `backend/lambdas/optimize_squad`
* `backend/lambdas/api`

Build, tag, and push to ECR as shown in Quickstart.

### Zip Lambda
* `backend/lambdas/ingest_fpl` → build a zip named `ingest_fpl.zip` and ensure stepfunctions.tf points to it.
_____________________________________________________________________


## Frontend
```shell
cd frontend/webapp
echo "VITE_API_BASE=https://<api-id>.execute-api.<region>.amazonaws.com" > .env
npm i && npm run build
# Host build/ with CloudFront+S3, Amplify, Netlify, etc.
```

The UI calls:
* `POST /optimize` (ad-hoc runs with constraints)
* `GET /squad` (fetch saved optimal squads)
* `GET /explain` (captaincy + meta)
_____________________________________________________________________


## Data Contracts

### Refined xPts Parquet (input to optimizer)
* Required columns:
    * `player_id` (int), `name` (string), `club_id` (int), `position` (string: GK/DEF/MID/FWD), `price` (double)
    * Either:
      * **Single-week**: `expected_points` (double)
      * **Multi-week**: `ep_w1`, `ep_w2`, …, `ep_wH` (double)
* Example (multi-week):

```text
player_id,name,club_id,position,price,ep_w1,ep_w2,ep_w3,ep_w4,ep_w5,ep_w6
123,Erling Haaland,11,FWD,14.0,7.2,8.1,7.8,6.9,7.0,7.4
...
```
> The pipeline’s Batch Transform can be configured to produce this exact schema.
_____________________________________________________________________


## API

Base URL (Terraform output): https://<api-id>.execute-api.<region>.amazonaws.com

## POST /optimize

Run an optimization immediately (and persist the result).

### Request (example):

```json
{
  "gameweek": 2,
  "variant": "user_specified",
  "budget": 100.0,
  "horizon": 6,
  "discount": 0.92,
  "max_per_club": 3,
  "captain_allowed_positions": ["MID","FWD"],
  "must_include_ids": [123],
  "must_exclude_ids": [999],
  "force_names": ["Salah"],        // optimize around specific player name(s)
  "positions_quota": {"GK":2,"DEF":5,"MID":5,"FWD":3},
  "xpts_s3": "s3://<refined-bucket>/refined/xpts/latest/players.parquet",
  "current_squad_ids": [ ... ],    // optional for transfer advice
  "free_transfers": 1,
  "transfer_cost": 4
}
```

### Response (truncated):

```json
{
  "status": "ok",
  "stored": {"pk":"GW#2","sk":"variant#user_specified"},
  "advice": {"out":[...],"in":[...],"hits":1,"points_penalty":4},
  "result": {
    "players": [{"player_id":123,"name":"...","position":"FWD","price":14.0}, ...],
    "captaincy": {"1":123,"2":321,...},
    "meta": {"objective": 94.12, "discount":0.92, "budget":100.0, "weeks":[1,2,3,4,5,6]}
  }
}
```

## GET /squad?gameweek={n}&variant={name}

Fetch the latest saved optimal squad.

## GET /explain?gameweek={n}&variant={name}

Returns captaincy per week and meta.
_____________________________________________________________________


## Optimizer Details
* Solver: OR-Tools CBC MILP.
* Decision variables:
  * $x_i ∈ {0,1}$ – select player i
  * $c_iw ∈ {0,1}$ – player i is captain in week w
* Objective (maximize discounted EP including captain doubling):

$[
\max \sum_{w=1}^{H} \gamma^{(w-1)} \left[ \sum_i (x_i \cdot EP_{i,w}) + \sum_i (c_{i,w} \cdot EP_{i,w}) \right]
]$
* Constraints:
  * Squad size: $Σ_i x_i = 15$
  * Positions: $Σ_{i∈pos} x_i = quota[pos]$
  * Budget: $Σ_i x_i * price_i ≤ budget$
  * Club limit: $∀club: Σ_{i∈club} x_i ≤ 3$
  * Captain: $∀w: Σ_i c_{i,w} = 1 and c_{i,w} ≤ x_i$
  * Optional: $c_{i,w} = 0$ if player’s position not in captain_allowed_positions
  * Must include/exclude by `player_id`
  * Optimize around names: $Σ_{i∈matches(force_names)} x_i ≥ 1$
_____________________________________________________________________


## Pipelines

### Scoring Pipeline (daily or pre-deadline)
1. Ingest FPL JSON → S3 (raw)
2. Feature Build (Lambda/SageMaker Processing) → S3 (refined)
3. Batch Inference (SageMaker Batch Transform) → multi-week EP parquet
4. Optimize (Lambda container with OR-Tools) → DynamoDB
5. Notify via SNS

### Training Pipeline (weekly/manual)
* Trains minutes and xPts (XGBoost), registers the xPts model in SageMaker Model Registry as Approved for batch inference.
___

## Security & Compliance
* Least-privilege IAM attached to Lambdas/Step Functions; restrict S3/DDB to resource ARNs in production.
* API Auth: add IAM/Cognito or JWT authorizer for private deployments.
* WAF on API Gateway (rate-limits, IP allowlists).
* Secrets: SSM Parameter Store / Secrets Manager (no hardcoding).
* PII: none stored. Data pertains to public football stats.
___

## Cost Notes
* Primarily serverless; costs dominated by:
* SageMaker Batch/Training (on-demand); choose small instance types and batch windows.
* Lambda invocations (cheap).
* S3 storage (raw/refined/batch output).
* DynamoDB on-demand (low unless heavy reads).
* Add AWS Budgets/alarms for spend visibility.
___

## Troubleshooting
* “No feasible solution”:
  * Budget too low, or conflicting constraints (e.g., must-include > 3 from same club). Loosen constraints or increase budget.
* “Missing ep_w columns”:
  * Provide either expected_points or ep_w1..ep_wH in the parquet.
* AccessDenied (S3/DDB):
  * Verify IAM policies and resource ARNs; ensure Terraform applied successfully.
* API 404 for /squad:
  * Run /optimize first or trigger the scoring pipeline to persist a squad.
___

## Roadmap
* Time-expanded ILP for transfer planning over multiple weeks (banking FTs).
* Automated model performance gates (approve/reject in Model Registry).
* CloudFront + S3 static hosting module in Terraform.
* QuickSight dashboard for EP trends and squad value tracking.
* Fan-out optimizations (multiple constraint scenarios in parallel).
___

## Contributing
1. Fork & clone
2. Create a feature branch: git checkout -b feat/my-improvement
3. Run lint/tests (add your own CI as needed)
4. PR to main

Please include:
* Clear description & motivation
* Testing notes or sample payloads
* If changing infra, include Terraform plan notes
___

## License

This repository is **not open-source**. No license is granted.

**All rights reserved © 2025 CeesarTech.**  
You may not copy, modify, distribute, or use any part of this code without prior written permission.  
For licensing inquiries, contact: chijiokekechi@gmail.com.

[![License: None](https://img.shields.io/badge/license-none-lightgrey.svg)](#license)
___

## Acknowledgements
* FPL official API endpoints (publicly accessible).
* Google OR-Tools.
* AWS Serverless + SageMaker stack.
___

## Maintainers
* **Primary**: Chijioke C. Ekechi ([![Chijioke on GitHub](https://img.shields.io/badge/GitHub-chijiokekechi-181717?logo=github)](https://github.com/chijiokekechi))
* Contributions welcome via PR.
