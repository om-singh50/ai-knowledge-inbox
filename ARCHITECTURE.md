# Architecture Overview

## Application Flow
1. **Ingestion:** Users submit plain-text notes or URLs via the frontend. The backend fetches URL content (if applicable), extracts text, and stores raw content with metadata (timestamp, source type).
2. **Processing:** The raw content is chunked into manageable pieces. Embeddings are generated for each chunk using a local `SentenceTransformer` model.
3. **Storage:** The raw content, chunks, and embeddings are stored in a local SQLite database.
4. **Querying:** A user submits a question. The backend generates an embedding for the question, performs a cosine similarity search against stored chunk embeddings, retrieves the top relevant chunks, and sends them along with the question to the Gemini API.
5. **Response:** Gemini generates an answer citing the provided context, which the backend returns to the frontend for display.

## Major Components
- **API Routes (`backend/app/api/`):** FastAPI endpoints for ingestion, listing items, and querying.
- **Services (`backend/app/services/`):** Business logic layer for RAG orchestration, URL fetching, content extraction, chunking, embedding generation, vector search, and Gemini generation.
- **Database Access (`backend/app/db/`):** SQLite database setup and session management.
- **Models & Schemas (`backend/app/models/`, `backend/app/schemas/`):** Database models and Pydantic schemas for request/response validation.
- **Core & Utils (`backend/app/core/`, `backend/app/utils/`):** Configuration, logging, and helper functions.
- **Frontend (`frontend/`):** React SPA providing the user interface for ingestion, listing, and querying.

## Data Flow (Ingestion to Query)
- **Ingest:** Frontend -> `POST /ingest` -> URL Fetcher (if URL) -> Chunker -> Embedding Generator (Gemini) -> SQLite (Items, Chunks, Embeddings).
- **Query:** Frontend -> `POST /query` -> Question Embedding (Gemini) -> Cosine Similarity Search (Python) -> Top-K Chunks -> Gemini API Prompt -> Answer -> Frontend.

## Design Decisions
**Why Python Linear Vector Search?**
This application uses a brute-force linear scan for vector similarity (Cosine Similarity) written in pure Python.
- **Why linear search:** It is ideal for a single-user application with a small dataset. It is easy to understand, requires no additional infrastructure, and avoids heavy numerical dependencies.
- **Complexity:** The computational complexity is approximately O(N × D), where N is the total number of stored chunks and D is the embedding dimension.
- **Scaling problem:** Because it performs a full table scan and calculates distance for every chunk, query latency grows linearly with the chunk count. SQLite is not a dedicated vector index, making this approach unsuitable for large datasets.

**Why SQLite?**
Using SQLite avoids the overhead of a dedicated database server (like PostgreSQL) while still providing robust relational data storage.

**Why Gemini for Embeddings?**
Initially planned for local `sentence-transformers`, the embedding provider was changed to the Gemini `gemini-embedding-001` API to avoid native ML binary dependencies (like PyTorch and transformers) that were being blocked by Windows Application Control in the local development environment. 
- Document chunks use `task_type="RETRIEVAL_DOCUMENT"`.
- User questions use `task_type="RETRIEVAL_QUERY"`.
- *Tradeoff*: Embedding generation now requires network/API availability, unlike local models.

**Text Chunking Strategy**
The application uses a simple, deterministic paragraph-aware chunking strategy. 
- **Paragraph boundaries first:** Preserving paragraphs maintains semantic context better than naive character splitting.
- **Maximum chunk size (~1000 characters):** Ensures chunks fit within the token limits of the embedding model and LLM context window.
- **Overlap (~150 characters):** Prevents edge cases where relevant information is split awkwardly across two chunks, ensuring continuity of context.
- **Simplicity:** For a single-user assignment, a custom deterministic function avoids heavy dependencies like LangChain while satisfying all requirements.

**What would change at a larger scale?**
- **Database:** Migrate from SQLite to a scalable RDBMS like PostgreSQL for concurrent user support.
- **Vector Search:** Migrate to PostgreSQL + pgvector or a dedicated vector database (e.g., Pinecone, Qdrant, Milvus) utilizing approximate nearest-neighbor indexes (ANN).
- **Asynchronous Processing:** Move content fetching, chunking, and embedding generation to background workers (e.g., Celery, Redis queue) to prevent blocking the API. Introduce background indexing where appropriate.
- **Authentication & Multi-tenancy:** Implement user authentication (e.g., OAuth2, JWT) and partition/filter data by user ID.
