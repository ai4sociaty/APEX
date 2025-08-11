#!/bin/bash

# Set environment variables
export VLLM_SERVER_URL="http://localhost:12000"
export FLUX_SERVER_URL="http://localhost:8000"
export VLLM_API_KEY="your_api_key"
export MONGO_URI="mongodb://localhost:27017/"
export MAX_ATTEMPTS=3

# Run the job manager
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1 --timeout-keep-alive 300