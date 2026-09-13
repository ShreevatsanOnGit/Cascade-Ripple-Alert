# CascadeMap

A disaster resilience simulator for critical infrastructure, built for the Manipal Hackathon 2026. 

CascadeMap simulates cascading infrastructure failures on a real city road network, showing human-impact numbers, an AI-written incident brief, and a round-by-round cascade replay as the visual centerpiece.

## Repository Structure
- `/backend`: FastAPI server handling data serving and core algorithms (shortest paths, cascading logic).
- `/frontend`: Next.js + Tailwind + Leaflet.js web application for interactive map visualization.
- `/ai`: AI/LLM endpoints for generating situation reports and parsing natural language queries.
- `/data`: Raw and processed city network JSON files.
- `/docs`: Pitch scripts, demo outlines, and architecture diagrams.

## How to Run Locally

You will need two terminal windows to run the application locally.

### Terminal 1: Backend (Python / FastAPI)
```bash
cd backend
# Create virtual environment (recommended)
python -m venv venv
# Activate it:
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
The backend will be running at `http://localhost:8000`

### Terminal 2: Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
The frontend will be running at `http://localhost:3000`
