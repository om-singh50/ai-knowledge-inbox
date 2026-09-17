import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.generation import generation_service, ContextChunk

def run_smoke_test():
    context = [
        ContextChunk(
            content="FastAPI is a Python framework used for building APIs and backend web services.",
            title="FastAPI Overview"
        )
    ]
    question = "What is FastAPI used for?"
    
    try:
        answer = generation_service.generate_answer(question, context)
        print("Generated Answer:\n" + answer)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_smoke_test()
