# Oregon Soccer Referee Concierge

An AI-powered concierge for Oregon soccer referees, providing quick answers about soccer rules, referee procedures, and Oregon-specific regulations.

## Project Structure

```
OSROAgent/
├── backend/           # FastAPI backend
│   ├── __init__.py
│   └── main.py        # API endpoints
├── frontend/          # Vite + React frontend
│   ├── public/
│   ├── src/
│   │   ├── App.jsx    # Main chat component
│   │   ├── index.css  # Tailwind CSS
│   │   └── main.jsx   # React entry point
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── data/              # Place documents here for ingestion
├── vector_store/      # Generated FAISS index
├── ingest.py          # Document ingestion script
├── requirements.txt   # Python dependencies
├── LICENSE
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google API Key for Gemini

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Add your Google API key to a `.env` file in the project root (e.g. `GOOGLE_API_KEY=your-api-key-here`). Docker Compose and the VS Code/Cursor launch config load it automatically; for running the backend directly, source `.env` or export the variable.

4. (Optional) Ingest documents for local use: add PDFs or text files to `data/`, then run `./ingest.py` to build `./vector_store`. For production, run `./ingest.py` then `./scripts/update-vector-store.sh` to sync the index to Cloud Run (see Production section).

5. Start the backend server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

## Usage

1. Add referee documents, rules PDFs, or text files to the `data/` directory
2. Run `./ingest.py` to create the vector store
3. Start the backend and frontend servers
4. Ask questions about soccer rules and referee procedures!

## Production (GCR / Cloud Run)

Images are tagged for **Google Container Registry**: `gcr.io/oregon-referees/osro-agent-api`, `gcr.io/oregon-referees/osro-agent-ui`. Deployments target project **oregon-referees**, region **us-west1**. The API reads the vector store from a **Cloud Storage bucket** mounted at `/app/vector_store`.

- **One-time setup (bucket and IAM):** Create the bucket and grant the Cloud Run service account access:
  ```bash
  ./scripts/setup-cloudrun-storage.sh
  ```
  Uses bucket `{PROJECT}-osro-vector-store` by default; set `VECTOR_STORE_BUCKET` to override.

- **Build and push to GCR:** From the project root, run:
  ```bash
  ./scripts/build-push.sh
  ```
  Optional: `TAG=sha-abc123 ./scripts/build-push.sh` to push a specific tag.

- **Deploy to Cloud Run:** After pushing images, set `GOOGLE_API_KEY` and run:
  ```bash
  ./scripts/deploy-cloudrun.sh
  ```
  The script deploys the API (with the GCS bucket mounted at `/app/vector_store`) first, then the UI with `BACKEND_URL` set to the API service URL.

- **Update only the vector store:** After changing documents and re-running ingest locally:
  ```bash
  ./ingest.py
  ./scripts/update-vector-store.sh
  ```
  This syncs `./vector_store` to the GCS bucket and deploys a new API revision so new instances load the updated index.

- **Local Docker:** `docker compose up` still builds and runs the app; the UI uses `BACKEND_URL=http://osro-agent-api:8000` by default. Local API uses the mounted `./vector_store` directory.

## License

MIT License - Copyright (c) 2026 William Kayser
