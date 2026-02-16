# Oregon Soccer Referee Concierge

An AI-powered concierge for Oregon soccer referees, providing quick answers about soccer rules, referee procedures, and Oregon-specific regulations.

**Live Application:** [https://oregonreferee.app](https://oregonreferee.app)

## Project Structure

```
OSROAgent/
├── backend/              # FastAPI backend
│   ├── __init__.py
│   ├── main.py           # API endpoints
│   ├── license_service.py # USSF license lookup
│   └── license_data.json # License reference data
├── frontend/             # Vite + React frontend
│   ├── public/
│   ├── src/
│   │   ├── App.jsx       # Main chat component
│   │   ├── index.css     # Tailwind CSS
│   │   └── main.jsx      # React entry point
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── scripts/              # Utility scripts (run via Task, not directly)
│   ├── ingest.py         # Document ingestion
│   ├── fetch_pages.py    # Download webpages as markdown
│   ├── build-push.sh     # Build and push Docker images
│   ├── deploy-cloudrun.sh # Deploy to Cloud Run
│   └── update-vector-store.sh # Sync vector store to GCS
├── data/                 # Source documents for ingestion
├── vector_store/         # Generated FAISS index
├── Taskfile.yml          # Build and deploy tasks (task ingest, task deploy-full, etc.)
├── requirements.txt      # Python dependencies
├── LICENSE
├── README.md
└── README-ingest.md      # Data ingestion guide
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

4. Start the backend server:
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

1. Start the backend and frontend servers
2. Ask questions about soccer rules and referee procedures!

## Training the Model

The AI assistant's knowledge comes from documents you provide. To learn how to add, update, and manage training data, see **[README-ingest.md](README-ingest.md)**.

## Build and deploy (Task)

Build and deploy are driven by [Task](https://taskfile.dev/). Scripts are intended to be run via Task, not invoked directly.

### First-time setup

1. **Install Task** (one-time per machine):
   - **macOS (Homebrew):** `brew install go-task`
   - **Linux:** `sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin` (ensure `~/.local/bin` is on your `PATH`)
   - **Windows:** `choco install go-task` or see [taskfile.dev/installation](https://taskfile.dev/installation/)
   - Verify: `task --version`

2. **No project-specific install:** Task is a single binary; no `npm install` or venv step for Task itself.

### Prepare your shell

Run task commands from the **project root** with your Python venv activated and tools (Docker, gcloud) available. Task loads `.env` from the project root automatically, so you do not need to `source .env` before running tasks.

### Commands

| Command | Description |
|---------|-------------|
| `task ingest` | Build the vector store from `data/` |
| `task build-push` | Build and push Docker images to GCR |
| `task update-vector-store` | Sync local `vector_store/` to GCS |
| `task deploy` | Deploy API and UI to Cloud Run |
| `task deploy-full` | Full pipeline: ingest → build-push → update-vector-store → deploy |
| `task fetch-pages` | Fetch URLs as markdown (e.g. `task fetch-pages -- --file data/fetch-and-edit.urls`) |
| `task setup-storage` | One-time: create GCS bucket and IAM for vector store |

Optional tag for build-push: `TAG=sha-abc123 task build-push`.

## Production (GCR / Cloud Run)

Images are tagged for **Google Container Registry**: `gcr.io/oregon-referees/osro-agent-api`, `gcr.io/oregon-referees/osro-agent-ui`. Deployments target project **oregon-referees**, region **us-west1**. The API reads the vector store from a **Cloud Storage bucket** mounted at `/app/vector_store`.

- **One-time setup (bucket and IAM):** Run `task setup-storage`. Uses bucket `{PROJECT}-osro-vector-store` by default; set `VECTOR_STORE_BUCKET` to override.

- **Full deploy:** From the project root (venv activated, `.env` with `GOOGLE_API_KEY`): run `task deploy-full`. This runs ingest, build-push, update-vector-store, and deploy in order.

- **Individual steps:** Use `task ingest`, `task build-push`, `task update-vector-store`, or `task deploy` as needed. After updating training data (see [README-ingest.md](README-ingest.md)), run `task update-vector-store` to sync the vector store to GCS.

- **Local Docker:** `docker compose up` still builds and runs the app; the UI uses `BACKEND_URL=http://osro-agent-api:8080` by default. Local API uses the mounted `./vector_store` directory. The app is at http://localhost:8000 (host port 8000 is the UI).

## License

MIT License - Copyright (c) 2026 William Kayser
