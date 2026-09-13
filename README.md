# CascadeMap (Phase 1 Prototype)

A disaster resilience simulator for critical infrastructure, built for the Manipal Hackathon 2026. 

CascadeMap simulates cascading infrastructure failures on a real city road network, showing human-impact numbers, an AI-written incident brief, and a round-by-round cascade replay as the visual centerpiece.

## The Problem
When disaster strikes, infrastructure failure isn't isolated. A power outage can knock out a water pumping station, which in turn leaves a hospital without critical resources. CascadeMap models these real-world dependencies to help emergency responders predict the ripple effect of failures and prioritize critical nodes for defense.

## Project Structure (Single Codebase)
We use a unified repository for all development phases:

- `backend/`: FastAPI server handling data serving and core algorithms (shortest paths, cascading logic).
- `frontend/`: Next.js + Tailwind + Leaflet.js web application for interactive map visualization.
- `data/`: Raw and processed city network JSON files (including the Manipal network).
- `docs/`: Pitch scripts, demo outlines, and architecture diagrams.
- `scripts/`: Data generation, processing, and maintenance scripts.
- `archive/`: Old prototypes and experiments (not used in the production app).

## How to Run Locally

You will need two terminal windows to run the application locally.

### Terminal 1: Backend (Python / FastAPI)
The backend uses Python. We recommend using a virtual environment.

```bash
cd backend
python -m venv venv

# Activate it:
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt

# To run using the Manipal dataset (Phase 1 Demo):
# Windows (PowerShell):
$env:NETWORK_JSON_PATH="../data/manipal_network.json"; uvicorn main:app --reload --port 8000
# Mac/Linux:
NETWORK_JSON_PATH="../data/manipal_network.json" uvicorn main:app --reload --port 8000
```
The backend API will run at `http://localhost:8000`

### Terminal 2: Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
The frontend will run at `http://localhost:3000`

## Team Git Workflow
We are working out of a SINGLE shared repository (`main` branch represents the stable core).
1. Always run `git pull origin phase-1` (or your active base branch) before starting work.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit frequently with clear messages.
4. Push your branch and open a Pull Request (PR) to merge changes safely.
