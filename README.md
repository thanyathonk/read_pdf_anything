# PDF RAG Chat

Chat with PDFs – text, tables, and images. Uses RAG to pull from your documents when answering questions.

## What it does

- Upload PDFs and ask questions about the content
- Handles text, tables, and images (auto-captions images)
- Select multiple PDFs and chat across them
- Ask general questions too (e.g. what is machine learning) without needing a PDF
- Guest mode or login (Google OAuth)
- Light/Dark theme

## Tech Stack

**Backend:** FastAPI, Unstructured (hi_res extraction), Ollama embeddings, ChromaDB, Groq LLM, MongoDB

**Frontend:** React 18 + Vite, Tailwind, Framer Motion

## How to run

### 1. Setup

```bash
# Backend
cd server
pip install -r requirements.txt

# Frontend
cd client
npm install
```

### 2. Environment files

In `server/` create `.env`:

```
MONGODB_URI=...
JWT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GROQ_API_KEY=...
```

In `client/` create `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=...
```

### 3. Start services

Ollama must be running for embeddings:

```bash
ollama serve
ollama pull qwen3-embedding:8b
```

Then run backend and frontend:

```bash
# Terminal 1
cd server && uvicorn main:app --reload --port 8000

# Terminal 2
cd client && npm run dev
```

Open http://localhost:5173 in your browser.

## Project structure

```
project/
├── client/          # React app
├── server/          # FastAPI backend
└── docs_archive/    # old docs
```

See `docs_archive/` and `SKILLS.md` for pipeline, chunking, and image captioning details.
