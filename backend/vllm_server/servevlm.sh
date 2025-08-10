#!/bin/bash
#
# vLLM Model Server Launcher
# Usage: ./servevlm.sh MODEL PORT API_KEY [MAX_SEQ_LENGTH] [GPU_UTIL]
# Example: ./servevlm.sh HuggingFaceTB/SmolVLM2-2.2B-Instruct 12000 mykey 36000 0.6

MODEL=${1:-HuggingFaceTB/SmolVLM2-2.2B-Instruct}
PORT=${2:-12000}
API_KEY=${3:-your_api_key}
MAX_SEQ_LENGTH=${4:-36000}
GPU_UTIL=${5:-0.6}

if [ -z "$MODEL" ] || [ -z "$PORT" ] || [ -z "$API_KEY" ]; then
  echo "Usage: $0 MODEL PORT API_KEY [MAX_SEQ_LENGTH] [GPU_UTIL]"
  echo "Example: $0 HuggingFaceTB/SmolVLM2-2.2B-Instruct 12000 mykey 36000 0.6"
  exit 1
fi

echo "Launching vLLM server with:"
echo "  Model: $MODEL"
echo "  Port: $PORT"
echo "  API Key: $API_KEY"
echo "  Max Seq Length: $MAX_SEQ_LENGTH"
echo "  GPU Utilization: $GPU_UTIL"

vllm serve \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --api-key "$API_KEY" \
    --gpu-memory-utilization "$GPU_UTIL" \
    --tensor-parallel-size 1 \
    --trust-remote-code \
    --max-batch-size 1 \
    --max-sequence-length "$MAX_SEQ_LENGTH"
    
