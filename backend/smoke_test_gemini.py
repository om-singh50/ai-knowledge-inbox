import os
import sys
from dotenv import load_dotenv
from app.services.embedding import embedding_service

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("Error: GEMINI_API_KEY is not set in the environment.")
        sys.exit(1)

    print("Running Gemini embedding smoke test...")
    try:
        vector = embedding_service.embed_document("This is a smoke test.")
        print(f"Success! Embedded text into vector.")
        print(f"Vector dimension: {len(vector)}")
    except Exception as e:
        print(f"Failed to run embedding smoke test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
