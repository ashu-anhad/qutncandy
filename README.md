# QutnCandy E-Commerce Portal (Scaffold)

This is a starter full-stack e-commerce scaffold for a clothing brand with:

- Frontend: React (Vite)
- Backend: Python FastAPI
- Database: PostgreSQL

## Project Structure

- frontend/ → React app
- backend/ → FastAPI app

## Local Development (No Docker)

### 1) Start PostgreSQL locally

Create a local PostgreSQL database and user:

- Database: `qutncandy`
- User: `qutn_user`
- Password: `qutn_password`
- Host: `localhost`
- Port: `5432`

You can use pgAdmin or `psql` for this step.

### 2) Backend setup

1. Create and activate a virtual environment
2. Install dependencies:
   - `pip install -r backend/requirements.txt`
3. Ensure config file exists:
   - `backend/.env` (already included)
4. Run API:
   - `uvicorn app.main:app --reload --app-dir backend`

Backend URL: http://localhost:8000  
API docs: http://localhost:8000/docs

### 3) Frontend setup

1. Install dependencies:
   - `cd frontend`
   - `npm install`
2. Run app:
   - `npm run dev`

Frontend URL: http://localhost:5173

## Starter API Endpoints

- GET /health
- GET /api/products
- POST /api/products

## Next Steps

- Add auth (customers/admin)
- Add product image upload
- Add cart + checkout workflow
- Add orders, payments, inventory models
- Add migrations with Alembic
- Add tests and CI/CD
