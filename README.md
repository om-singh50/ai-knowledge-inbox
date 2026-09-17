# AI Knowledge Inbox

AI Knowledge Inbox is a simple, single-user web application designed for personal knowledge management. It allows users to save plain-text notes and URLs, extract their content, generate embeddings using the Gemini API, and use Retrieval-Augmented Generation (RAG) to ask questions and receive answers based on the ingested knowledge.

## Architecture

The system consists of a REST API backend that manages data ingestion, embedding generation, and RAG logic, alongside a React frontend user interface for interaction.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** SQLite
- **Embeddings:** Gemini API via `google-genai`
- **Similarity Search:** In-memory linear cosine similarity (Python)
- **LLM:** Gemini API via `google-genai`
- **Frontend:** React, Vite, Tailwind CSS

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## How to Run

### Backend

1. Navigate to the `backend/` directory.
2. Install dependencies (e.g. `pip install -r requirements.txt`).
3. Run the development server: `uvicorn app.main:app --reload`
The backend will be available at `http://localhost:8000`.

### Frontend

1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`
The frontend will be available at `http://localhost:5173`.

## API Endpoints

- `POST /ingest`: Accepts a note (text) or a URL. For URLs, it fetches the content. It then chunks the text, calls the Gemini API to generate embeddings, and saves the chunks, embeddings, and metadata to the database.
- `GET /items`: Lists all saved knowledge items (notes and URLs) with their metadata.
- `POST /query`: Accepts a user question. It embeds the question, retrieves the most relevant chunks using cosine similarity, and passes the chunks as context to the Gemini API to generate an answer with cited sources.

## RAG Flow

The application follows a standard Retrieval-Augmented Generation (RAG) pipeline:
1. **Ingestion:** User submits a URL or plain-text note. Content is extracted.
2. **Chunking:** The content is split into smaller, overlapping chunks.
3. **Gemini Embeddings:** Each chunk is sent to the Gemini API to generate a vector embedding.
4. **SQLite:** Chunks, embeddings, and metadata are persisted in a SQLite database.
5. **Cosine Retrieval:** When a user queries, the question is embedded, and the most relevant chunks are found using a linear cosine similarity search in Python.
6. **Gemini Generation:** The retrieved chunks are provided as context to a Gemini model to generate a natural language response.
7. **Answer + Sources:** The generated answer and the source chunks used are returned to the user.

## Design Decisions

- **SQLite + Linear Cosine Search:** Chosen for simplicity and zero-configuration setup for a local, single-user environment. Since the expected dataset is small (personal notes), a full vector database is unnecessary overhead. The embeddings are loaded into memory and compared using simple vector math, which is fast for small-scale datasets.
- **Chunking Strategy:** Content is split into chunks of fixed character length with a slight overlap. This preserves context across chunk boundaries while ensuring chunks fit within embedding model limits and provide granular retrieval.
- **Dev-Environment Focus:** The app is built to run entirely locally without complex infrastructure (like Docker or external DBs), utilizing free-tier AI API resources (Gemini API) rather than requiring heavy local GPUs for embeddings or LLM inference. Note that this application does not include authentication and is not intended for production-scale deployment.

## Scaling Considerations

To scale this application for multiple users or large knowledge bases, the following changes would be required:
- **Vector Database:** Replace SQLite and in-memory linear search with a dedicated vector database (e.g., Pinecone, Milvus, Qdrant, pgvector) for efficient approximate nearest neighbor (ANN) search.
- **Background Workers:** Move document ingestion, fetching, and embedding generation into background tasks (e.g., Celery) to prevent blocking the API.
- **Authentication & Authorization:** Add user authentication and ensure users can only query their own ingested knowledge.
- **Production Infrastructure:** Deploy using Docker, use a production ASGI server like Gunicorn, and use a robust relational database (e.g., PostgreSQL) for application metadata.
