# 🏗️ ArchitectIQ

<p align="center">

**Backend Architecture Analysis System for Production AI Applications**

Analyze AI architectures, evaluate production readiness, estimate infrastructure costs, and generate optimization recommendations through REST APIs.

</p>

<p align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![MIT License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</p>

---

# 🌐 Live Demo

| Service | URL |
|---------|-----|
| Frontend | https://architectiq-liard.vercel.app |
| Backend API | https://architectiq.onrender.com |
| Swagger Docs | https://architectiq.onrender.com/docs |

---

# 📌 Overview

ArchitectIQ is a FastAPI-based backend system that analyzes AI application architectures and generates production-ready engineering insights.

It evaluates system scalability, security, reliability, infrastructure cost, and production readiness before generating structured recommendations and implementation roadmaps.

Designed for developers, AI engineers, startups, and autonomous agents, ArchitectIQ exposes REST APIs returning structured JSON responses suitable for both human and machine consumption.

---

# 🚀 Features

- Architecture Health & Production Readiness Analysis
- Infrastructure & AI Cost Estimation
- Security, Reliability & Scalability Audit
- Optimization Recommendation Engine
- Executive Summary & Implementation Roadmap
- AI-Agent Friendly JSON Responses
- OpenAPI (Swagger) Documentation

---

# 🏗️ System Architecture

![Architecture](screenshots/architecture-diagram.png)

---

# ⚙️ Backend Pipeline

```text
User / AI Agent
       │
       ▼
 FastAPI REST API
       │
 ┌─────┼─────────────┐
 │     │             │
 ▼     ▼             ▼
Architecture   Cost      Recommendation
 Analyzer     Engine        Engine
 │
 ▼
Executive Summary
 │
 ▼
Optimization Roadmap
 │
 ▼
Structured JSON Response
```

---

# 🔌 REST API

| Method | Endpoint | Description |
|----------|------------------|--------------------------------|
| GET | `/health` | Health Check |
| POST | `/api/v1/review` | Analyze Architecture |
| POST | `/api/v1/estimate` | Estimate Infrastructure Cost |
| POST | `/api/v1/recommend` | Generate Recommendations |

Swagger UI:

```
/docs
```

---

# 🛠 Tech Stack

| Layer | Technologies |
|--------|--------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI, Python, Pydantic |
| Deployment | Render, Vercel |

---

# 📸 Screenshots

## Landing Page

![Landing](screenshots/landing_page1.png)

---

## Architecture Review

![Review](screenshots/review_page1.png)

---

## Executive Report

![Report](screenshots/report_page1.png)

---

## JSON API Response

![JSON](screenshots/report_page4.png)

---

# 📂 Project Structure

```text
ArchitectIQ
│
├── backend/
├── frontend/
├── screenshots/
└── README.md
```

---

# 🚀 Run Locally

## Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Runs at

```
http://localhost:8000
```

## Frontend

```bash
cd frontend

npm install

npm run dev
```

Runs at

```
http://localhost:5173
```

---

# 🎯 Highlights

- Modular FastAPI backend architecture
- REST APIs with OpenAPI (Swagger)
- Structured JSON API responses
- Pydantic request validation
- Production readiness evaluation
- Infrastructure cost estimation
- Recommendation engine for AI systems

---

MIT License
