"""
Main entry point for the Walking AI Assistant application
"""
import uvicorn
import os
import argparse
from api import app

def main():
    """Run the Walking AI Assistant application"""
    parser = argparse.ArgumentParser(description="Walking AI Assistant")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server")
    parser.add_argument("--db-path", type=str, default="walking_assistant.db", help="Path to the SQLite database")
    parser.add_argument("--cache-dir", type=str, default="cache", help="Directory for caching data")
    parser.add_argument("--model-name", type=str, default="meta-llama/Llama-2-7b-chat-hf", help="LLM model name")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["DB_PATH"] = args.db_path
    os.environ["CACHE_DIR"] = args.cache_dir
    os.environ["MODEL_NAME"] = args.model_name
    
    # Run the server
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
