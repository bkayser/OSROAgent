# OSROAgent Architecture

## Project Structure

```
OSROAgent/
├── frontend/          # React frontend application
│   ├── public/       # Static assets (logos, images)
│   └── src/          # React components and logic
├── backend/          # Python backend application
│   └── ...           # Flask API and business logic
├── scripts/          # Utility scripts
├── ingest.py         # Data ingestion script
├── run.py            # Application runner
├── Dockerfile        # Container definition
└── docker-compose.yml # Multi-container setup
```

## Frontend Architecture
- Framework: React
- Location: `/frontend`
- Static Assets: `/frontend/public`
- Build Tool: [Vite/Create React App - to be confirmed]

## Backend Architecture
- Framework: Python/Flask
- Location: `/backend`
- API Structure: RESTful endpoints

## Deployment
- **Local Development**: 
  - Backend and frontend can be launched separately from Cursor using launch configurations
  - Docker Desktop available for containerized development
- **Production**: Deployed at https://oregonreferee.app
- Uses `docker-compose` for orchestration

## Key Integration Points
- Backend API serves data to frontend
- Static assets (logos, images) served from `/frontend/public`
- CORS configuration allows frontend-backend communication