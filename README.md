# CodeCompass

CodeCompass is a Chrome extension that lets developers ask natural-language questions about any GitHub repository they're browsing — public or private — without cloning it locally. It uses retrieval-augmented generation (RAG) to ground every answer in the actual codebase, with inline file and line-number citations.

## What it does

- Detects the GitHub repo you're currently viewing in Chrome
- Indexes the repo on demand via the GitHub API (no local clone required)
- Answers questions about the codebase using semantic search over embedded code, documentation, and configuration files
- Cites the specific file and line numbers behind every answer
- Refuses to answer questions it can't ground in the indexed content, rather than guessing

## Tech stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL with `pgvector` for vector similarity search
- **Embeddings:** `sentence-transformers` (local, no external API cost)
- **Answer generation:** Google Gemini API
- **Repo access:** GitHub API (on-demand fetching, supports public and private repos with a scoped token)
- **Frontend:** Chrome Extension, Manifest V3 (vanilla HTML/CSS/JS popup)

## Architecture

1. **Chunking** — repo files are split into overlapping line-based chunks (`chunker.py`), covering source code, README/documentation, and configuration files (YAML, TOML, Dockerfiles, etc).
2. **Embedding** — each chunk is embedded locally using `sentence-transformers` and stored in Postgres alongside its file path, line range, and repo URL (`embeddings.py`).
3. **Retrieval** — when a question is asked, the most semantically similar chunks are retrieved via vector distance search, with README content always included to support project-level questions.
4. **Generation** — retrieved chunks are assembled into a prompt and sent to Gemini, which is instructed to answer only from the provided context and cite its sources (`generate.py`).
5. **Extension** — the popup detects the active GitHub repo, triggers indexing if needed, and provides a chat interface for asking questions (`extension/`).

## Project structure

```
CodeCompass/
├── backend/
│   ├── app.py            # Flask API (/health, /index, /ask)
│   ├── chunker.py         # File chunking logic
│   ├── embeddings.py      # Embedding generation, storage, retrieval
│   ├── generate.py        # Prompt construction and Gemini integration
│   └── github_fetcher.py  # On-demand repo fetching via GitHub API
├── extension/
│   ├── manifest.json
│   ├── popup.html
│   ├── popup.js
│   └── icon16.png / icon48.png / icon128.png
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL with the `pgvector` extension enabled
- A Gemini API key
- A GitHub personal access token (read-only, scoped to the repos you need)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with:

```
GEMINI_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
```

Set up the database:

```sql
CREATE DATABASE codecompass;
CREATE EXTENSION vector;
```

Run the backend:

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

### Extension

1. Go to `chrome://extensions`
2. Enable Developer Mode
3. Click "Load unpacked" and select the `extension/` folder
4. Open any GitHub repository page and click the CodeCompass icon

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/index` | POST | Index a repo. Body: `{ "repo_url": "...", "force": false }` |
| `/ask` | POST | Ask a question. Body: `{ "question": "...", "repo_url": "..." }` |

## License

MIT# codecompass-private-test
