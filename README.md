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