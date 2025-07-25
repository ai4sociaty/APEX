# Job Manager Service - FastAPI
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from bson import ObjectId
import uuid
import json
import os
import shutil
from datetime import datetime

app = FastAPI(title="Job Manager Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Mount static files directory for serving uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# MongoDB connection
DATABASE = {"jobs": []}  # Fallback in-memory storage
try:
    # For local MongoDB (current setup)
    # client = MongoClient("mongodb://localhost:27017/")
    
    # For remote MongoDB (uncomment and update with your remote server details)
    # client = MongoClient("mongodb://remote-server:27017/")
    
    # For MongoDB Atlas (cloud)
    # client = MongoClient("mongodb+srv://username:password@cluster.mongodb.net/")
    
    # For authenticated MongoDB
    # client = MongoClient("mongodb://username:password@server:27017/")
    
    client = MongoClient("mongodb://localhost:27017/")  # Current setup
    db = client.apex_database
    jobs_collection = db.jobs
    profiles_collection = db.profiles
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    # Fallback to in-memory storage
    jobs_collection = None
    profiles_collection = None

# Updated models to match frontend data structure
class BasicInfo(BaseModel):
    purpose: Optional[str] = None
    attire: Optional[str] = None
    background: Optional[str] = None
    vibe: Optional[str] = None

class AdvancedSettings(BaseModel):
    lighting: Optional[str] = None
    mood: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    ethnicity: Optional[str] = None
    resolution: Optional[str] = None

class AdditionalInfo(BaseModel):
    reference_photo: Optional[str] = None
    custom_notes: Optional[str] = None
    preset_used: Optional[str] = None

class Metadata(BaseModel):
    timestamp: Optional[str] = None
    version: Optional[str] = None
    created_by: Optional[str] = None

class CreateJobRequest(BaseModel):
    basic_info: Optional[BasicInfo] = None
    advanced_settings: Optional[AdvancedSettings] = None
    additional_info: Optional[AdditionalInfo] = None
    metadata: Optional[Metadata] = None
    generated_prompt: Optional[str] = None
    # Legacy fields for backward compatibility
    prompt: Optional[str] = None
    style: Optional[str] = "portrait"
    seed: Optional[int] = None

class JobRecord(BaseModel):
    job_id: str
    prompt: str
    style: str
    seed: Optional[int] = None
    status: str
    image_url: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None

@app.post("/jobs")
async def create_job(
    profile_data: str = Form(...),
    reference_photo: UploadFile = File(None)
):
    # Log the raw request data for debugging
    print(f"Profile data: {profile_data}")
    print(f"Reference photo: {reference_photo.filename if reference_photo else 'None'}")
    
    try:
        # Parse the profile data
        data = json.loads(profile_data)
        print(f"Parsed JSON: {data}")
        
        job_id = str(uuid.uuid4())
        
        # Handle reference photo upload
        reference_photo_url = None
        reference_photo_path = None
        if reference_photo and reference_photo.filename:
            # Save the uploaded file
            file_extension = os.path.splitext(reference_photo.filename)[1]
            file_name = f"{job_id}_reference{file_extension}"
            file_path = os.path.join("uploads", file_name)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(reference_photo.file, buffer)
            
            reference_photo_url = f"http://localhost:8000/uploads/{file_name}"
            reference_photo_path = file_path
            print(f"Saved reference photo: {reference_photo_url}")
        
        # Extract prompt from generated_prompt or fallback to legacy prompt field
        prompt = data.get("generated_prompt") or data.get("prompt", "Default portrait")
        
        # Create job record
        job = {
            "job_id": job_id,
            "prompt": prompt,
            "style": data.get("style", "portrait"),
            "seed": data.get("seed", None),
            "status": "pending",
            "image_url": None,
            "reference_photo_url": reference_photo_url,
            "reference_photo_path": reference_photo_path,
            "profile_data": data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save to MongoDB if available, otherwise use in-memory storage
        if jobs_collection is not None:
            try:
                result = jobs_collection.insert_one(job)
                job["_id"] = str(result.inserted_id)
                print(f"✅ Job saved to MongoDB: {job_id}")
                
                # Also save the profile separately for better querying
                profile_record = {
                    "job_id": job_id,
                    "profile_data": data,
                    "created_at": datetime.utcnow()
                }
                profiles_collection.insert_one(profile_record)
                print(f"✅ Profile saved to MongoDB: {job_id}")
                
            except Exception as mongo_error:
                print(f"❌ MongoDB save failed: {mongo_error}")
                # Fallback to in-memory storage
                DATABASE["jobs"].append(job)
        else:
            # Fallback to in-memory storage
            DATABASE["jobs"].append(job)
            print(f"⚠️ Saved to memory (MongoDB not available): {job_id}")
        
        print(f"Created job: {job_id}")
        
        # TODO: Call Flux server here and update job status/image_url
        return {"job_id": job_id, "status": "pending", "reference_photo_url": reference_photo_url}
        
    except Exception as e:
        print(f"Error creating job: {e}")
        return {"error": str(e)}, 400

@app.get("/jobs")
def list_jobs():
    """Get all jobs from MongoDB or memory"""
    if jobs_collection is not None:
        try:
            jobs = list(jobs_collection.find({}, {"_id": 0}))  # Exclude MongoDB _id field
            return {"jobs": jobs}
        except Exception as e:
            print(f"❌ MongoDB read failed: {e}")
            # Fallback to memory
            return {"jobs": DATABASE.get("jobs", [])}
    else:
        return {"jobs": DATABASE.get("jobs", [])}

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Get a specific job by ID from MongoDB or memory"""
    if jobs_collection is not None:
        try:
            job = jobs_collection.find_one({"job_id": job_id}, {"_id": 0})
            if job:
                return job
            return {"error": "Job not found"}
        except Exception as e:
            print(f"❌ MongoDB read failed: {e}")
            # Fallback to memory
            for job in DATABASE.get("jobs", []):
                if job["job_id"] == job_id:
                    return job
            return {"error": "Job not found"}
    else:
        for job in DATABASE.get("jobs", []):
            if job["job_id"] == job_id:
                return job
        return {"error": "Job not found"}

@app.get("/profiles")
def list_profiles():
    """Get all profiles from MongoDB"""
    if profiles_collection is not None:
        try:
            profiles = list(profiles_collection.find({}, {"_id": 0}))
            return {"profiles": profiles}
        except Exception as e:
            print(f"❌ MongoDB read failed: {e}")
            return {"profiles": [], "error": str(e)}
    else:
        return {"profiles": [], "error": "MongoDB not available"}

@app.get("/profiles/{job_id}")
def get_profile(job_id: str):
    """Get a specific profile by job ID"""
    if profiles_collection is not None:
        try:
            profile = profiles_collection.find_one({"job_id": job_id}, {"_id": 0})
            if profile:
                return profile
            return {"error": "Profile not found"}
        except Exception as e:
            print(f"❌ MongoDB read failed: {e}")
            return {"error": str(e)}
    else:
        return {"error": "MongoDB not available"}

@app.get("/stats")
def get_stats():
    """Get database statistics"""
    stats = {
        "mongodb_connected": jobs_collection is not None,
        "total_jobs": 0,
        "total_profiles": 0,
        "jobs_with_photos": 0
    }
    
    if jobs_collection is not None:
        try:
            stats["total_jobs"] = jobs_collection.count_documents({})
            stats["total_profiles"] = profiles_collection.count_documents({})
            stats["jobs_with_photos"] = jobs_collection.count_documents({"reference_photo_url": {"$ne": None}})
        except Exception as e:
            stats["error"] = str(e)
    else:
        stats["total_jobs"] = len(DATABASE.get("jobs", []))
        stats["jobs_with_photos"] = len([j for j in DATABASE.get("jobs", []) if j.get("reference_photo_url")])
    
    return stats

@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    """Delete a specific job and its associated profile"""
    if jobs_collection is not None:
        try:
            # Get job details first to clean up files
            job = jobs_collection.find_one({"job_id": job_id})
            if job and job.get("reference_photo_path"):
                # Delete the physical file
                try:
                    os.remove(job["reference_photo_path"])
                    print(f"Deleted file: {job['reference_photo_path']}")
                except:
                    pass
            
            # Delete from MongoDB
            job_result = jobs_collection.delete_one({"job_id": job_id})
            profile_result = profiles_collection.delete_one({"job_id": job_id})
            
            if job_result.deleted_count > 0:
                return {"message": f"Job {job_id} deleted successfully"}
            else:
                return {"error": "Job not found"}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"error": "MongoDB not available"}

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Simple web dashboard to view MongoDB data"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>APEX Job Manager Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #1976d2; }
            .stat-label { color: #666; margin-top: 5px; }
            .jobs-grid { display: grid; gap: 20px; }
            .job-card { background: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 15px; }
            .job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
            .job-id { font-weight: bold; color: #1976d2; }
            .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
            .status-pending { background: #fff3cd; color: #856404; }
            .status-completed { background: #d1edff; color: #0c5460; }
            .refresh-btn { background: #1976d2; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #1565c0; }
            .photo-link { color: #1976d2; text-decoration: none; }
            .photo-link:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🖼️ APEX Job Manager Dashboard</h1>
            
            <div id="stats" class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-jobs">-</div>
                    <div class="stat-label">Total Jobs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-profiles">-</div>
                    <div class="stat-label">Profiles</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="jobs-with-photos">-</div>
                    <div class="stat-label">Jobs with Photos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="mongodb-status">-</div>
                    <div class="stat-label">MongoDB Status</div>
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>Recent Jobs</h2>
                <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
            </div>
            
            <div id="jobs-container" class="jobs-grid">
                <p>Loading jobs...</p>
            </div>
        </div>

        <script>
            async function loadData() {
                try {
                    // Load stats
                    const statsResponse = await fetch('/stats');
                    const stats = await statsResponse.json();
                    
                    document.getElementById('total-jobs').textContent = stats.total_jobs;
                    document.getElementById('total-profiles').textContent = stats.total_profiles;
                    document.getElementById('jobs-with-photos').textContent = stats.jobs_with_photos;
                    document.getElementById('mongodb-status').textContent = stats.mongodb_connected ? '✅ Connected' : '❌ Disconnected';
                    
                    // Load jobs
                    const jobsResponse = await fetch('/jobs');
                    const jobsData = await jobsResponse.json();
                    
                    const container = document.getElementById('jobs-container');
                    if (jobsData.jobs && jobsData.jobs.length > 0) {
                        container.innerHTML = jobsData.jobs.map(job => `
                            <div class="job-card">
                                <div class="job-header">
                                    <span class="job-id">🔗 ${job.job_id}</span>
                                    <span class="status status-${job.status}">${job.status.toUpperCase()}</span>
                                </div>
                                <p><strong>📝 Prompt:</strong> ${job.prompt.substring(0, 100)}${job.prompt.length > 100 ? '...' : ''}</p>
                                <p><strong>🎨 Style:</strong> ${job.style}</p>
                                ${job.reference_photo_url ? `<p><strong>📸 Photo:</strong> <a href="${job.reference_photo_url}" target="_blank" class="photo-link">View Reference</a></p>` : ''}
                                <p><strong>📅 Created:</strong> ${new Date(job.created_at).toLocaleString()}</p>
                                ${job.profile_data ? `<details><summary>📋 Profile Data</summary><pre style="background: #f0f0f0; padding: 10px; border-radius: 4px; overflow: auto; max-height: 200px;">${JSON.stringify(job.profile_data, null, 2)}</pre></details>` : ''}
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = '<p>No jobs found.</p>';
                    }
                } catch (error) {
                    console.error('Error loading data:', error);
                    document.getElementById('jobs-container').innerHTML = '<p style="color: red;">Error loading data. Check console for details.</p>';
                }
            }
            
            // Load data on page load
            loadData();
            
            // Auto-refresh every 30 seconds
            setInterval(loadData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/export/all")
def export_all_data():
    """Export all data as a single JSON file"""
    if jobs_collection is not None:
        try:
            jobs = list(jobs_collection.find({}, {"_id": 0}))
            profiles = list(profiles_collection.find({}, {"_id": 0}))
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "total_jobs": len(jobs),
                "total_profiles": len(profiles),
                "jobs": jobs,
                "profiles": profiles
            }
            
            return export_data
        except Exception as e:
            return {"error": str(e)}
    else:
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_jobs": len(DATABASE.get("jobs", [])),
            "total_profiles": 0,
            "jobs": DATABASE.get("jobs", []),
            "profiles": [],
            "note": "MongoDB not available, using memory data"
        }

@app.get("/export/jobs")
def export_jobs_only():
    """Export only jobs data"""
    if jobs_collection is not None:
        try:
            jobs = list(jobs_collection.find({}, {"_id": 0}))
            return {"jobs": jobs, "count": len(jobs)}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"jobs": DATABASE.get("jobs", []), "count": len(DATABASE.get("jobs", []))}

@app.get("/export/profiles")  
def export_profiles_only():
    """Export only profiles data"""
    if profiles_collection is not None:
        try:
            profiles = list(profiles_collection.find({}, {"_id": 0}))
            return {"profiles": profiles, "count": len(profiles)}
        except Exception as e:
            return {"error": str(e)}
    else:
        return {"profiles": [], "count": 0}
#after setting up mongo

@app.get("/jobs/pending")
def get_pending_jobs():
    """Get all jobs with pending status for vLLM server to process"""
    if jobs_collection is not None:
        try:
            pending_jobs = list(jobs_collection.find(
                {"status": "pending"}, 
                {"_id": 0}
            ).sort("created_at", 1))  # Oldest first
            return {"pending_jobs": pending_jobs, "count": len(pending_jobs)}
        except Exception as e:
            print(f"❌ Error fetching pending jobs: {e}")
            return {"pending_jobs": [], "count": 0, "error": str(e)}
    else:
        # Fallback to memory
        pending = [job for job in DATABASE.get("jobs", []) if job.get("status") == "pending"]
        return {"pending_jobs": pending, "count": len(pending)}

@app.put("/jobs/{job_id}/status")
def update_job_status(job_id: str, status: str, image_url: str = None, error_message: str = None):
    """Allow vLLM server to update job status and results"""
    if jobs_collection is not None:
        try:
            update_data = {
                "status": status, 
                "updated_at": datetime.utcnow()
            }
            
            if image_url:
                update_data["image_url"] = image_url
            if error_message:
                update_data["error_message"] = error_message
                
            result = jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Job {job_id} status updated to: {status}")
                return {"message": f"Job {job_id} status updated to {status}"}
            else:
                return {"error": "Job not found"}
        except Exception as e:
            print(f"❌ Error updating job status: {e}")
            return {"error": str(e)}
    else:
        # Fallback to memory
        for job in DATABASE.get("jobs", []):
            if job["job_id"] == job_id:
                job["status"] = status
                job["updated_at"] = datetime.utcnow()
                if image_url:
                    job["image_url"] = image_url
                if error_message:
                    job["error_message"] = error_message
                return {"message": f"Job {job_id} status updated to {status}"}
        return {"error": "Job not found"}

@app.get("/jobs/processing")
def get_processing_jobs():
    """Get all jobs currently being processed"""
    if jobs_collection is not None:
        try:
            processing_jobs = list(jobs_collection.find(
                {"status": "processing"}, 
                {"_id": 0}
            ))
            return {"processing_jobs": processing_jobs, "count": len(processing_jobs)}
        except Exception as e:
            return {"processing_jobs": [], "count": 0, "error": str(e)}
    else:
        processing = [job for job in DATABASE.get("jobs", []) if job.get("status") == "processing"]
        return {"processing_jobs": processing, "count": len(processing)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
