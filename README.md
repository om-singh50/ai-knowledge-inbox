# AI Knowledge Inbox

AI Knowledge Inbox is a full-stack, single-user Retrieval-Augmented Generation (RAG) application. It allows users to save plain-text notes and extract content from URLs, automatically chunking and embedding the information into a local knowledge base to answer natural language questions with source citations.

## Features

- **Ingestion**: Supports plain-text note ingestion and URL ingestion with server-side fetching and HTML content extraction.
- **RAG Pipeline**: Deterministic chunking, semantic retrieval, and grounded answer generation using Gemini models.
- **Vector Storage**: Lightweight SQLite storage with a custom Python-based linear cosine similarity search.
- **Frontend**: Responsive React UI (built with Vite and Tailwind CSS) featuring validation, loading states, error handling, and empty states.
- **Citations**: Returns exact source snippets and relevance scores used to generate the answer.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, Pydantic, httpx, BeautifulSoup, `google-genai`
- **Frontend**: React, Vite, Tailwind CSS

## Architecture

```text
  [ React Frontend ]
         │
         ▼ (HTTP POST /ingest, POST /query)
  [ FastAPI Backend ]
         │
         ├─► Ingestion Service (Extract, Chunk, Embed)
         │         │
         │         ▼
         │   [ SQLite DB (Documents + Embeddings) ]
         │
         └─► Query Service
                   │
                   ├─► 1. Embed user question
                   ├─► 2. Retrieve top-K chunks (Linear Cosine Similarity)
                   └─► 3. Generate answer (Gemini) with source metadata
```

## RAG Pipeline

1. **Ingestion Flow (Notes)**: The raw text is directly normalized, chunked, and embedded.
2. **Ingestion Flow (URLs)**: The server fetches the URL, validates the content type, strips HTML noise (scripts, styles, headers), and extracts readable text before chunking and embedding.
3. **Query Flow**: Retrieval happens strictly *before* generation. The system embeds the user's question, performs a linear search over stored embeddings to find the most relevant chunks, and then passes those specific chunks to the generation model. Source metadata (URL, title, snippet) is constructed deterministically by the application logic, not fabricated by the AI.

## Chunking Strategy

- **Strategy**: Paragraph-aware deterministic chunking.
- **Size Constraints**: Approximately 1,000-character maximum chunks with a ~150-character overlap.
- **Why**: Preserves semantic context across paragraph boundaries without exceeding model context window constraints. Overlap ensures that concepts split across two chunks retain contextual continuity.
- **Tradeoff**: Very large single paragraphs without natural breaks may be split mid-sentence.

## Vector Storage and Search

- **Implementation**: Embeddings are stored as BLOB/JSON in a standard SQLite database. Search is implemented in Python using exact linear cosine similarity calculation.
- **Complexity**: $O(N \times D)$ where $N$ is the number of chunks and $D$ is the embedding dimensionality.
- **Why**: For a single-user assignment or small personal knowledge base, a linear scan in memory is sufficiently fast and avoids the heavy dependency of a dedicated vector database (like Qdrant or Milvus).
- **Scale**: At scale (millions of documents), this approach would become a bottleneck and require an Approximate Nearest Neighbor (ANN) index.

## AI Models

- **Embedding Model**: `gemini-embedding-001`
- **Generation Model**: `gemini-3.6-flash`
- **Considerations**: The application requires a valid Google Gemini API key. Rate limits and quota constraints of the Gemini API apply. Embeddings are generated remotely via the API.

## URL Extraction and Security

The URL extraction pipeline includes several protections:
- **Server-side Fetch**: Uses asynchronous `httpx` fetching.
- **Security**: Validates schemes (`http`/`https`) and explicitly rejects localhost or private IP addresses to prevent Server-Side Request Forgery (SSRF).
- **Resilience**: 10-second timeout, maximum of 5 redirects, and a strict 5 MB response size limit.
- **Parsing**: Uses `BeautifulSoup` to strip non-content tags and extract core article text.

## API Documentation

### `POST /ingest`
Ingests a new document into the knowledge base.
- **Example Request (Note)**:
  ```json
  {
    "source_type": "note",
    "title": "Meeting Notes",
    "content": "Discussed the new RAG architecture..."
  }
  ```
- **Example Request (URL)**:
  ```json
  {
    "source_type": "url",
    "url": "https://example.com/article"
  }
  ```
- **Validation**: Enforces that `content` cannot be provided for URLs, and `url` cannot be provided for notes.
- **Example Response**:
  ```json
  {
    "id": "uuid-1234",
    "source_type": "url",
    "title": "Example Domain",
    "url": "https://example.com/article",
    "created_at": "2026-09-17T10:00:00Z",
    "chunk_count": 3
  }
  ```

### `GET /items`
Retrieves a list of all saved knowledge items.
- **Example Response**:
  ```json
  [
    {
      "id": "uuid-1234",
      "source_type": "url",
      "title": "Example Domain",
      "source": "https://example.com/article",
      "created_at": "2026-09-17T10:00:00Z"
    }
  ]
  ```

### `POST /query`
Asks a question against the knowledge base.
- **Example Request**:
  ```json
  {
    "question": "What is the new RAG architecture?"
  }
  ```
- **Example Response**:
  ```json
  {
    "answer": "The new architecture uses SQLite and Gemini models...",
    "sources": [
      {
        "document_id": "uuid-1234",
        "source_type": "note",
        "title": "Meeting Notes",
        "url": null,
        "content": "Discussed the new RAG architecture...",
        "relevance_score": 0.89
      }
    ]
  }
  ```

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/        # FastAPI routers
│   │   ├── core/       # Configuration
│   │   ├── db/         # SQLite database and repository
│   │   ├── schemas/    # Pydantic models
│   │   └── services/   # Chunking, scraping, embedding, RAG logic
│   ├── tests/          # Test suite
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/ # React components
    │   └── App.jsx     # Main layout
    ├── package.json
    └── vite.config.js
```

## Setup and Installation

### 1. Backend Setup
Navigate to the `backend` directory and set up the Python environment:
```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

Set up the required environment variables by creating a `.env` file in the `backend` directory:
```env
GEMINI_API_KEY="your_api_key_here"
```
*(Do not commit this `.env` file to version control.)*

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

### 2. Frontend Setup
Navigate to the `frontend` directory:
```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend` directory:
```env
VITE_BACKEND_URL="http://127.0.0.1:8000"
```
*(Do not commit this `.env` file to version control.)*

Start the Vite development server:
```bash
npm run dev
```

To create a production build:
```bash
npm run build
```

## Testing

The backend includes a comprehensive automated test suite (14 test files) covering unit and integration tests across routers, database, services, and schemas. External network calls (`httpx` scraping) and AI API calls (`google-genai`) are mocked to ensure reliable and fast execution without relying on live endpoints.

Run the tests using `pytest` (ensure the virtual environment is active):
```bash
cd backend
pytest tests/
```

## Manual Verification

The following flows have been manually verified:
- **Note Ingestion**: Successful creation, chunking, and embedding of text notes.
- **URL Ingestion**: Successful fetching, content extraction, and embedding of valid URLs; proper error handling of invalid/timeout URLs.
- **Querying**: Semantic retrieval returning contextually relevant snippets that correctly ground the LLM answer.
- **Source Display**: React UI correctly presents the answer along with metadata and original chunks.
- **No-evidence Behavior**: The system gracefully handles queries lacking relevant internal knowledge by stating it cannot answer based on provided context.

## Design Decisions and Tradeoffs

- **No Authentication**: The assignment scope implies a single-user system, avoiding the complexity of auth and multi-tenancy.
- **SQLite + Linear Search**: Using SQLite avoids the operational overhead of managing a dedicated vector database or background workers. Linear search is highly performant for small datasets but trades off scalability.
- **Simple Chunking**: A deterministic character/paragraph-based chunking strategy was chosen over complex NLP-based chunking libraries to minimize dependencies and maintain full control over the logic.
- **Direct Service Separation**: The architecture explicitly separates chunking, embedding, scraping, and RAG services, keeping the implementation clean without overengineering with abstraction-heavy frameworks.

## Scaling Considerations

To evolve this application for production scale, the following changes would be required:
1. **Vector Infrastructure**: As the document count grows, the $O(N \times D)$ linear search would degrade latency. This would necessitate migrating to a dedicated vector database with Approximate Nearest Neighbor (ANN) indexing.
2. **Relational Database**: Migrate SQLite to PostgreSQL for better concurrency handling and data integrity.
3. **Background Processing**: Synchronous URL fetching and embedding during the `POST /ingest` request will timeout on large sites. Ingestion should move to an asynchronous background worker queue.
4. **Authentication & Multi-tenancy**: Adding users requires robust authentication and tenancy filtering on vector retrieval.
5. **Rate Limiting & Observability**: Implement strict API rate limiting and comprehensive telemetry to monitor LLM token usage and latency.
