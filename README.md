# Catering Environment Behavior Detection

A web application with a Vue 3 + Vite frontend and a Django backend for behavior detection in catering environments.

## Tech Stack
- Frontend: Vue 3, Vite (JavaScript)
- Backend: Django (recommend 4.2 LTS for Python 3.9)
- Database: SQLite (development)
- OS: Windows/macOS/Linux

## Project Structure
- `frontend/`: Vue app
- `backend/`: Django project

## Prerequisites
- Node.js ≥ 18 (with npm ≥ 9)
- Python ≥ 3.9

## Quick Start

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Build and preview:
```bash
npm run build
npm run preview
```

### Janus Analysis Service
```bash
Download Janus-Pro-1B (or Janus-Pro-7B): https://huggingface.co/deepseek-ai/Janus-Pro-1B/tree/main
CATERING-ENVIRONMENT-BEHAVIOR-DETECTION-MAIN\BACKEND\MODELS
│  l_version_1_300.pt
│
└─janus-pro-1b
        config.json
        gitattributes
        janus_pro_teaser1.png
        janus_pro_teaser2.png
        preprocessor_config.json
        processor_config.json
        pytorch_model.bin
        README.md
        special_tokens_map.json
        tokenizer.json
        tokenizer_config.json
cd backend
cd Janus
pip install -e .
cd ..
python janus_query_service.py
```

### Backend
```bash 
cd backend
# (optional) create & activate venv
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## License
MIT License. See `LICENSE`.
