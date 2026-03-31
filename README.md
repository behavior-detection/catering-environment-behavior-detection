# Catering Environment Behavior Detection System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)
[![Node.js 18](https://img.shields.io/badge/Node.js-18%2B-brightgreen.svg)](https://nodejs.org/)
[![Django 4.2](https://img.shields.io/badge/Django-4.2-blue.svg)](https://www.djangoproject.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/)

> A real-time catering kitchen monitoring system powered by YOLOv8 object detection, integrating video stream analysis, violation event management, AI-powered querying, and multi-role access control.

---

## Core Features

- **Real-Time Video Monitoring** — Live PPE compliance checks (mask, hat, uniform) and prohibited item detection (phone, cigarette, mouse) via YOLOv8
- **ROI Configuration** — Custom polygon-based detection regions
- **Violation Management** — Auto snapshot, confirmation, false alarm marking, batch upload, and export
- **Analytics Dashboard** — Trend charts, camera comparisons, and hourly distribution (ECharts)
- **AI Natural Language Query** — Query violation data in plain language (Janus/Flask)
- **Multi-Role Auth** — Admin / Manager / Visitor with email verification and security questions
- **Face Recognition Login** — Optional face-based authentication
- **Enterprise OCR** — ID card and business license recognition (Java Spring Boot)
- **WebRTC Data Sharing** — P2P file sharing between Manager and Visitor
- **Token Access Control** — Admin-managed access tokens for controlled data sharing

---

## Architecture

### System Components

```mermaid
flowchart TB
    subgraph Client["Client"]
        Browser["Browser"]
    end

    subgraph Frontend["Frontend :5174"]
        Vue["Vue 3 + Vite\nElement Plus / ECharts / Vuex"]
    end

    subgraph Backend["Application Layer"]
        Django["Django 4.2 / Daphne ASGI\n:8081"]
        Celery["Celery Worker"]
    end

    subgraph Microservices["Microservices"]
        Janus["Janus Query\nFlask :5001"]
        Face["Face Recognition\nFlask :5000"]
        OCR["Java OCR\nSpring Boot :8080"]
    end

    subgraph AI["AI"]
        YOLO["YOLOv8 Custom Model\n7 Classes"]
    end

    subgraph Data["Data"]
        MySQL[("MySQL 8.0 :3306")]
        Redis[("Redis 5.x :6379")]
    end

    Browser <-->|HTTP / WS| Vue
    Vue <-->|REST / WebSocket| Django
    Django -->|Dispatch Tasks| Celery
    Django <-->|Query API| Janus
    Django <-->|Auth API| Face
    Django <-->|OCR API| OCR
    Celery -->|Inference| YOLO
    Celery <-->|Broker / Cache| Redis
    Django <-->|Channel Layer / Session| Redis
    Django <-->|ORM| MySQL
    Janus <-->|SQL| MySQL
```

### Real-Time Detection Flow

```mermaid
sequenceDiagram
    actor User
    participant Vue as Vue Frontend
    participant WS as Django Channels
    participant Celery as Celery Worker
    participant YOLO as YOLOv8
    participant Redis
    participant DB as MySQL

    User->>Vue: Open monitoring page
    Vue->>WS: Connect ws/video/{source_id}/
    WS->>Celery: Dispatch detection task

    loop Every Frame (8 FPS)
        Celery->>YOLO: Run inference
        YOLO-->>Celery: Detections (bbox, class, conf)
        alt Violation Detected
            Celery->>DB: Save ViolationEvent
            Celery->>Redis: Publish alert
            Redis-->>WS: Channel Layer broadcast
            WS-->>Vue: Push violation + annotated frame
        else No Violation
            Celery->>Redis: Cache annotated frame
            Redis-->>WS: Broadcast
            WS-->>Vue: Push live frame
        end
    end

    User->>Vue: Stop monitoring
    Vue->>WS: Stop command
    WS->>Celery: Revoke task
```

### AI Query Flow

```mermaid
sequenceDiagram
    actor User
    participant Vue as Vue Frontend
    participant Django
    participant Janus as Janus Query :5001
    participant DB as MySQL

    User->>Vue: Natural language query
    Vue->>Django: POST /api/monitor/ai-query/
    Django->>Janus: Forward request
    Janus->>DB: Generate and execute SQL
    DB-->>Janus: Results
    Janus-->>Django: Structured response
    Django-->>Vue: JSON
    Vue-->>User: Charts + text answer
```

### YOLO Detection Classes

| Class | Logic |
|---|---|
| `person` | Baseline for PPE checks |
| `mask` `hat` `uniform` | Not on person → violation |
| `mouse` `phone` `cigarette` | Presence → violation |

---

## Quick Start

### Requirements

- **Node.js** >= 18 · **Python** >= 3.9 · **MySQL** >= 8.0 · **Redis** >= 5.0
- Optional: **Java JRE** >= 8 (OCR) · **CUDA** (GPU acceleration)

### 1. Database

```sql
CREATE DATABASE kitchen_detection_system CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE kitchen_detection_system;
SOURCE backend/kitchen_detection_system.sql;
```

### 2. Backend

```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env                           # Edit with your credentials
python manage.py migrate
python start_all_services.py                   # One-click launch
```

This starts **Redis → Java OCR → Django (Daphne :8081) → Janus (:5001) → Face Service (:5000) → Celery Worker** in sequence.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5174
```

### Key Environment Variables (`backend/.env`)

| Variable | Required | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | — |
| `DB_PASSWORD` | Yes | — |
| `DB_NAME` / `DB_USER` / `DB_HOST` / `DB_PORT` | | `kitchen_detection_system` / `root` / `127.0.0.1` / `3306` |
| `REDIS_HOST` / `REDIS_PORT` | | `127.0.0.1` / `6379` |
| `PYTHON_APP_PORT` | | `8081` |
| `YOLO_DEVICE` | | `cpu` |

---

## Project Structure

```
├── frontend/                         # Vue 3 + Vite
│   ├── src/components/               # UI components (login, monitor, permissions...)
│   ├── src/views/                    # Page views
│   ├── src/services/                 # API layer & WebRTC clients
│   ├── store/                        # Vuex modules
│   └── vite.config.js                # Dev proxy config
│
├── backend/                          # Django 4.2
│   ├── core/                         # Settings, URLs, ASGI, Celery
│   ├── apps/monitor/                 # Violations, AI query, permissions, WebRTC
│   ├── apps/login/                   # Auth, user API, face recognition
│   ├── detection/                    # YOLO module (model, consumers, tasks)
│   │   └── yolo/weights/best.pt      # Custom YOLOv8 weights
│   ├── face_service/                 # Face recognition (Flask)
│   ├── janus_query_service.py        # AI query service (Flask)
│   ├── lib/                          # Java OCR JAR
│   ├── start_all_services.py         # One-click launcher
│   ├── kitchen_detection_system.sql  # DB init script
│   ├── requirements.txt
│   └── .env.example                  # Env template
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

[MIT License](LICENSE). Third-party: [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) (AGPL-3.0), [PyTorch](https://github.com/pytorch/pytorch) (BSD-3-Clause).
