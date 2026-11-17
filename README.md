# CineMatch: AI-Powered Movie Recommendation System

CineMatch is a production-grade, enterprise-scale movie recommendation platform built with **FastAPI**, **React**, **MongoDB**, **Redis**, and **Apache Spark MLlib**.

---

## 🏛️ System Architecture

```
                                      +------------------------+
                                      |   MovieLens 100K       |
                                      +------------------------+
                                                  |
                                                  v
                                      +------------------------+
                                      |   Apache Spark MLlib   |
                                      |  (ALS Factorization)   |
                                      +------------------------+
                                                  |
                                                  v
+------------------------+            +------------------------+
|      React + Vite      | <=======>  |     FastAPI Server     | <=======> [ MongoDB ]
|      Tailwind CSS      |  REST API  |  (Asynchronous Engine) |
+------------------------+            +------------------------+
                                                  ^
                                                  |
                                                  v
                                           [ Redis Cache ]
```

---

## 📂 Project Structure

```
Cluster_computing/
├── backend/            # FastAPI asynchronous REST backend
│   ├── app/            # Application code (core, api, models, schemas, services)
│   └── requirements.txt
├── frontend/           # React + Vite + Tailwind CSS SPA
│   ├── src/            # Components, pages, context, services
│   └── package.json
├── ml_engine/          # PySpark ML pipeline & factor models
│   ├── pipelines/      # Ingestion, training, evaluation, inference
│   ├── data/           # Raw and processed datasets (MovieLens 100K)
│   └── utils/          # SparkSession builder
└── scripts/            # Environment validation & data download automation
```

---

## 🚀 Quickstart Guide

### 1. Verify Environment
```bash
python scripts/verify_environment.py
```

### 2. Download MovieLens 100K Dataset
```bash
python scripts/download_movielens.py
```

### 3. Run Backend (FastAPI)
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Open interactive Swagger docs at: `http://localhost:8000/docs`

### 4. Run Frontend (React + Vite)
```bash
cd frontend
npm.cmd install
npm.cmd run dev
```
Open the web app at: `http://localhost:5173`
