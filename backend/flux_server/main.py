import torch
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from PIL import Image
import io
import threading
import base64
from contextlib import asynccontextmanager

# Global threading lock for model safety
model_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once at startup and clean up resources"""
    global pipe
    print("🖼️ Loading Flux image generation model...")
    try:
        # Load model with safety settings
        pipe = FluxKontextPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-Kontext-dev",
            torch_dtype=torch.bfloat16,
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe.to("cuda")
        pipe.enable_model_cpu_offload()
        pipe.enable_xformers_memory_efficient_attention()
        print("✅ Model successfully loaded!")
    except Exception as e:
        print(f"❌ Model loading failed: {str(e)}")
        raise RuntimeError("Could not load model") from e
    yield
    # Clean up GPU resources
    print("🧹 Cleaning up resources...")
    del pipe
    torch.cuda.empty_cache()
    print("✅ Cleanup complete!")

app = FastAPI(
    lifespan=lifespan,
    title="FLUX.1 Kontext API",
    description="Image editing API using FluxKontextPipeline",
    version="1.0"
)

def generate_image(input_image: Image.Image, prompt: str, guidance_scale: float) -> Image.Image:
    """Thread-safe image generation function"""
    try:
        with model_lock:
            # Process image with model
            return pipe(
                image=input_image,
                prompt=prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=30
            ).images[0]
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            torch.cuda.empty_cache()
            raise HTTPException(500, "GPU memory overflow - try smaller image")
        raise

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": "pipe" in globals()}

@app.post("/generate")
async def generate_image_endpoint(
    prompt: str = Form(..., description="Text prompt for image generation"),
    job_id: str = Form(None, description="Job ID for tracking"),
    image_file: UploadFile = File(None, description="Image file (PNG/JPEG)"),
    image_url: str = Form(None, description="Image URL"),
    guidance_scale: float = Form(2.5, description="Guidance scale (1.0-10.0)")
) -> JSONResponse:
    """
    Generate an image from a prompt and an input image.
    Returns: JSON with job_id and base64-encoded PNG image.
    """
    if not image_file and not image_url:
        raise HTTPException(400, "Either image_file or image_url required")
    if image_file and image_url:
        raise HTTPException(400, "Use only one image source (file or URL)")
    
    try:
        # Load input image
        if image_file:
            if image_file.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(400, "Invalid file type. Use JPEG or PNG")
            input_image = Image.open(io.BytesIO(await image_file.read()))
        else:
            input_image = load_image(image_url)
        
        # Validate image dimensions
        if max(input_image.size) > 2048:
            raise HTTPException(400, "Image dimensions too large (max 2048px)")
        if min(input_image.size) < 64:
            raise HTTPException(400, "Image dimensions too small (min 64px)")
        
        # Process image using thread pool
        output_image = await run_in_threadpool(
            generate_image,
            input_image,
            prompt,
            guidance_scale
        )
        
        # Return PNG image as base64 in JSON
        img_bytes = io.BytesIO()
        output_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        img_b64 = base64.b64encode(img_bytes.read()).decode("utf-8")
        return {"job_id": job_id, "image_base64": img_b64}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=120
    )