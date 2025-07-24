# CUDA_VISIBLE_DEVICES=0 vllm serve MODEL \
#     --host 0.0.0.0 \
#     --port PORT \
#     --max-model-len MAX_SEQ_LENGTH \
#     --api-key YOUR_API_KEY \
#     --gpu-memory-utilization=FRAC_OF_VRAM \
#     --tensor-parallel-size 1 \
#     --trust-remote-code


# bin/bash
# Usage: ./servevlm.sh MODEL PORT MAX_SEQ_LENGTH YOUR_API_KEY FRAC_OF
#Serve SmolVLM2 2.2B 
vllm serve \
    --model  HuggingFaceTB/SmolVLM2-2.2B-Instruct \
    --host 0.0.0.0 \
    --port 12000 \
    --api-key API_KEY \
    --gpu-memory-utilization 0.6 \
    --tensor-parallel-size 1 \
    --trust-remote-code \
    --max-batch-size 1 \
    --max-sequence-length 36000 \
    
