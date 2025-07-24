import torch
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response
from fastapi.concurrency import run_in_threadpool
from diffusers import FluxKontextPipeline
from diffusers.utils import load_image
from PIL import Image
import io
import threading
from contextlib import asynccontextmanager

# Global threading lock for model safety
model_lock = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once at startup and clean up resources"""
    global pipe
    print("Loading model...")
    try:
        # Load model with safety settings
        pipe = FluxKontextPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-Kontext-dev",
            torch_dtype=torch.bfloat16,
            safety_checker=None,  # Disable safety checker for performance
            requires_safety_checker=False
        )
        pipe.to("cuda")
        pipe.enable_model_cpu_offload()  # Optimize GPU memory
        pipe.enable_xformers_memory_efficient_attention()  # Reduce VRAM usage
        print("Model successfully loaded!")
    except Exception as e:
        print(f"Model loading failed: {str(e)}")
        raise RuntimeError("Could not load model") from e
    yield
    # Clean up GPU resources
    print("Cleaning up resources...")
    del pipe
    torch.cuda.empty_cache()
    print("Cleanup complete!")

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
                num_inference_steps=30  # Optimal step count for quality/speed
            ).images[0]
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            torch.cuda.empty_cache()
            raise HTTPException(500, "GPU memory overflow - try smaller image")
        raise

@app.post("/generate", response_class=Response)
async def generate_image_endpoint(
    prompt: str = Form(..., description="Text prompt for image editing", example="Add a hat to the cat"),
    guidance_scale: float = Form(2.5, description="Guidance scale (1.0-20.0)", example=2.5),
    image_file: UploadFile = File(None, description="Image file (PNG/JPEG)"),
    image_url: str = Form(None, description="Image URL", example="https://example.com/cat.png")
) -> Response:
    """
    Generate edited image based on input image and text prompt
    
    - **prompt**: Text instruction for image editing (required)
    - **guidance_scale**: Controls creativity vs prompt adherence (default 2.5)
    - **image_file**: Upload image file (either file or URL required)
    - **image_url**: Fetch image from URL (either file or URL required)
    
    Returns: PNG image with edits applied
    """
    # Validate inputs
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

        # Return PNG image
        img_bytes = io.BytesIO()
        output_image.save(img_bytes, format="PNG")
        return Response(content=img_bytes.getvalue(), media_type="image/png")

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
        timeout_keep_alive=120  # Important for long-running requests
    )