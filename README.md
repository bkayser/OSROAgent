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

3. Set your Google API key:
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

4. (Optional) Ingest documents:
   ```bash
   # Add documents to the data/ folder first
   python ingest.py
   ```
   If you had an existing `vector_store/` from a previous version, remove it and re-run `ingest.py` (embedding model may have changed).

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
2. Run `python ingest.py` to create the vector store
3. Start the backend and frontend servers
4. Ask questions about soccer rules and referee procedures!

## License

MIT License - Copyright (c) 2026 William Kayser
