import os
import uuid
import json
import base64
import httpx
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job_manager")

# Load environment variables
VLLM_SERVER_URL = os.getenv("VLLM_SERVER_URL", "http://localhost:12000")
FLUX_SERVER_URL = os.getenv("FLUX_SERVER_URL", "http://localhost:8000")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "your_api_key")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", 3))

app = FastAPI(
    title="APEX Job Manager Service",
    description="Orchestrates portrait generation workflow",
    version="1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    client = MongoClient(MONGO_URI)
    db = client.apex_jobs
    jobs_collection = db.jobs
    logger.info("✅ Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    # Fallback to in-memory storage
    jobs_collection = None
    JOBS_DB = []

# Models
class JobStatus(BaseModel):
    status: str = Field(..., description="Current job status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class JobAttempt(BaseModel):
    attempt: int
    prompt: str
    image_base64: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    status: JobStatus

class JobRecord(BaseModel):
    job_id: str
    original_image_base64: str
    parameters: Dict[str, Any]
    attempts: List[JobAttempt] = []
    current_status: JobStatus
    final_image_base64: Optional[str] = None
    report: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ValidationRequest(BaseModel):
    original_image_base64: str
    generated_image_base64: str
    parameters: Dict[str, Any]
    conditions: Dict[str, Any]

class VLLMRequest(BaseModel):
    model: str = "gpt-4-vision-preview"
    messages: List[Dict[str, Any]]
    max_tokens: int = 4096

# Utility functions
def save_job_to_db(job: dict):
    if jobs_collection:
        try:
            result = jobs_collection.insert_one(job)
            job["_id"] = str(result.inserted_id)
            logger.info(f"✅ Job {job['job_id']} saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save failed: {e}")
            JOBS_DB.append(job)
    else:
        JOBS_DB.append(job)
        logger.info(f"⚠️ Job {job['job_id']} saved to memory")

def update_job_in_db(job_id: str, update_data: dict):
    if jobs_collection:
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"✅ Job {job_id} updated in MongoDB")
                return True
        except Exception as e:
            logger.error(f"❌ MongoDB update failed: {e}")
    
    # Fallback for in-memory storage
    for job in JOBS_DB:
        if job["job_id"] == job_id:
            job.update(update_data)
            job["updated_at"] = datetime.utcnow()
            logger.info(f"⚠️ Job {job_id} updated in memory")
            return True
    return False

def get_job_from_db(job_id: str):
    if jobs_collection:
        try:
            job = jobs_collection.find_one({"job_id": job_id})
            if job:
                job["_id"] = str(job["_id"])  # Convert ObjectId to string
                return job
        except Exception as e:
            logger.error(f"❌ MongoDB fetch failed: {e}")
    
    # Fallback for in-memory storage
    for job in JOBS_DB:
        if job["job_id"] == job_id:
            return job
    return None

async def call_vllm_server(messages: List[Dict[str, Any]]) -> str:
    """Call vLLM server to generate text response"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": messages,
            "max_tokens": 4096
        }
        headers = {
            "Authorization": f"Bearer {VLLM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(
                f"{VLLM_SERVER_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"vLLM API error: {str(e)}")
            raise HTTPException(500, f"vLLM service error: {str(e)}")

async def call_flux_server(image_base64: str, prompt: str) -> str:
    """Call Flux server to generate image"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # For direct image upload
            files = {"image_file": ("image.png", base64.b64decode(image_base64), "image/png")}
            data = {"prompt": prompt}
            
            response = await client.post(
                f"{FLUX_SERVER_URL}/generate",
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()
            return result["image_base64"]
        except Exception as e:
            logger.error(f"Flux API error: {str(e)}")
            raise HTTPException(500, f"Image generation service error: {str(e)}")

async def validate_image(original_image_base64: str, generated_image_base64: str, parameters: dict) -> dict:
    """Validate generated image using vLLM server"""
    system_prompt = """
    You are an AI image quality validator. Your task is to evaluate a generated portrait against 
    the original image and generation parameters. Provide a JSON response with:
    - "valid": boolean (true if image meets quality standards)
    - "score": integer (1-100 quality score)
    - "issues": list of strings (any quality issues found)
    - "tuned_prompt": string (improved prompt for next attempt if needed)
    
    Evaluation criteria:
    1. Faithfulness to original facial features
    2. Adherence to parameters: {parameters}
    3. Visual quality and artifacts
    4. Composition and aesthetics
    """
    
    user_prompt = """
    Please evaluate the generated portrait image based on the original reference image and 
    the following parameters: {parameters}
    """
    
    messages = [
        {
            "role": "system",
            "content": system_prompt.format(parameters=json.dumps(parameters, indent=2))
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt.format(parameters=json.dumps(parameters))},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{original_image_base64}"}
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{generated_image_base64}"}
                }
            ]
        }
    ]
    
    response = await call_vllm_server(messages)
    try:
        # Extract JSON from response
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        return json.loads(response[start_idx:end_idx])
    except json.JSONDecodeError:
        logger.error(f"Failed to parse validation response: {response}")
        return {"valid": False, "score": 0, "issues": ["Validation failed"], "tuned_prompt": ""}

async def generate_report(job_id: str) -> dict:
    """Generate final report for failed jobs"""
    job = get_job_from_db(job_id)
    if not job:
        return {"error": "Job not found"}
    
    system_prompt = """
    You are an AI portrait generation analyst. Create a detailed failure report including:
    - "summary": string (brief failure summary)
    - "attempt_analysis": list of objects (each with attempt number, issues, score)
    - "root_causes": list of strings (probable root causes)
    - "recommendations": list of strings (suggested improvements)
    """
    
    user_prompt = f"""
    Analyze this failed portrait generation job (ID: {job_id}). 
    Parameters: {json.dumps(job['parameters'], indent=2)}
    
    Attempt history:
    {json.dumps(job['attempts'], indent=2)}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response = await call_vllm_server(messages)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Failed to generate report", "raw_response": response}

# Background task for job processing
async def process_job(job_id: str):
    logger.info(f"🚀 Starting job processing: {job_id}")
    job = get_job_from_db(job_id)
    if not job:
        logger.error(f"Job not found: {job_id}")
        return
    
    # Update job status to processing
    update_data = {
        "current_status": {"status": "processing", "timestamp": datetime.utcnow()}
    }
    update_job_in_db(job_id, update_data)
    
    # Get job data
    original_image_base64 = job["original_image_base64"]
    parameters = job["parameters"]
    attempts = []
    
    # Main processing loop
    for attempt_num in range(MAX_ATTEMPTS):
        logger.info(f"🔁 Attempt {attempt_num+1}/{MAX_ATTEMPTS} for job {job_id}")
        
        # Create attempt record
        attempt = {
            "attempt": attempt_num + 1,
            "status": {"status": "processing", "timestamp": datetime.utcnow()}
        }
        
        try:
            # Step 1: Generate prompt with vLLM
            logger.info("  ⚙️ Generating prompt...")
            prompt = await generate_prompt(original_image_base64, parameters)
            attempt["prompt"] = prompt
            
            # Step 2: Generate image with Flux
            logger.info("  🎨 Generating image...")
            generated_image_base64 = await call_flux_server(
                original_image_base64, 
                prompt
            )
            attempt["image_base64"] = generated_image_base64
            
            # Step 3: Validate results
            logger.info("  🔍 Validating results...")
            validation_result = await validate_image(
                original_image_base64,
                generated_image_base64,
                parameters
            )
            attempt["validation_result"] = validation_result
            
            # Update attempt status
            attempt["status"] = {
                "status": "completed", 
                "timestamp": datetime.utcnow()
            }
            
            # Store attempt
            attempts.append(attempt)
            update_job_in_db(job_id, {"attempts": attempts})
            
            # Check validation result
            if validation_result.get("valid", False):
                logger.info(f"✅ Validation passed for job {job_id}")
                update_job_in_db(job_id, {
                    "current_status": {"status": "completed", "timestamp": datetime.utcnow()},
                    "final_image_base64": generated_image_base64
                })
                return
                
            logger.info(f"⚠️ Validation failed for job {job_id}: {validation_result.get('issues', ['Unknown'])}")
            
            # Use tuned prompt for next attempt if available
            if tuned_prompt := validation_result.get("tuned_prompt"):
                parameters["prompt"] = tuned_prompt
        
        except Exception as e:
            logger.error(f"❌ Attempt {attempt_num+1} failed: {str(e)}")
            attempt["status"] = {
                "status": "failed", 
                "timestamp": datetime.utcnow(),
                "error": str(e)
            }
            attempts.append(attempt)
            update_job_in_db(job_id, {"attempts": attempts})
    
    # If all attempts failed
    logger.info(f"❌ All attempts failed for job {job_id}")
    update_job_in_db(job_id, {
        "current_status": {"status": "failed", "timestamp": datetime.utcnow()}
    })
    
    # Generate failure report
    logger.info("📊 Generating failure report...")
    report = await generate_report(job_id)
    update_job_in_db(job_id, {"report": report})

async def generate_prompt(image_base64: str, parameters: dict) -> str:
    """Generate prompt using vLLM server"""
    system_prompt = """
    You are a professional portrait photographer assistant. Create detailed prompts for 
    portrait generation based on the reference image and these parameters:
    
    Parameters:
    {parameters}
    
    Prompt requirements:
    1. Describe the person's appearance faithfully to the reference image
    2. Incorporate all specified parameters
    3. Add artistic details about lighting, mood, and background
    4. Use 50-100 words
    """
    
    user_prompt = """
    Create a portrait generation prompt based on this reference image and the provided parameters.
    """
    
    messages = [
        {
            "role": "system",
            "content": system_prompt.format(parameters=json.dumps(parameters, indent=2))
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        }
    ]
    
    return await call_vllm_server(messages)

# API Endpoints
@app.post("/jobs", response_model=dict)
async def create_job(
    background_tasks: BackgroundTasks,
    image_file: UploadFile = File(..., description="Reference image"),
    parameters: str = Form(..., description="Generation parameters as JSON")
):
    """Create a new portrait generation job"""
    try:
        # Read and encode image
        image_data = await image_file.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Parse parameters
        params = json.loads(parameters)
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Create job record
        job_record = {
            "job_id": job_id,
            "original_image_base64": image_base64,
            "parameters": params,
            "current_status": {
                "status": "pending",
                "timestamp": datetime.utcnow()
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save to database
        save_job_to_db(job_record)
        
        # Add to background processing
        background_tasks.add_task(process_job, job_id)
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Job created and processing started"
        }
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid parameters format")
    except Exception as e:
        raise HTTPException(500, f"Job creation failed: {str(e)}")

@app.get("/jobs/{job_id}", response_model=dict)
def get_job_status(job_id: str):
    """Get current status of a job"""
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Remove large fields for status check
    response = job.copy()
    response.pop("original_image_base64", None)
    for attempt in response.get("attempts", []):
        attempt.pop("image_base64", None)
    response.pop("final_image_base64", None)
    
    return response

@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str):
    """Get final result of a completed job"""
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job["current_status"]["status"] != "completed":
        raise HTTPException(400, "Job not completed yet")
    
    if not job.get("final_image_base64"):
        raise HTTPException(500, "Final image missing")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "image_base64": job["final_image_base64"]
    }

@app.get("/jobs/{job_id}/report")
def get_job_report(job_id: str):
    """Get report for a failed job"""
    job = get_job_from_db(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job["current_status"]["status"] != "failed":
        raise HTTPException(400, "Job not failed")
    
    if not job.get("report"):
        raise HTTPException(404, "Report not available")
    
    return {
        "job_id": job_id,
        "status": "failed",
        "report": job["report"]
    }

@app.get("/health")
def health_check():
    """Service health check"""
    services = {
        "vllm_server": "unknown",
        "flux_server": "unknown",
        "database": "unknown"
    }
    
    # Check MongoDB connection
    if jobs_collection:
        try:
            # Simple ping command
            jobs_collection.database.command('ping')
            services["database"] = "healthy"
        except Exception as e:
            services["database"] = f"unhealthy: {str(e)}"
    else:
        services["database"] = "in-memory"
    
    return {
        "status": "running",
        "services": services
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        timeout_keep_alive=300
    )