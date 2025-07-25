# 🔗 APEX Backend - Database & vLLM Connection Guide

## 📋 Table of Contents
- [How to Run Everything](#how-to-run-everything)
- [Database Setup](#database-setup)
- [MongoDB Access Methods](#mongodb-access-methods)
- [Data Export/Import](#data-exportimport)
- [vLLM Independent Server Integration](#vllm-independent-server-integration)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)

--
## 🚀 How to Run Everything

### **🎯 Complete System Startup Guide**

This section provides step-by-step instructions to run the entire APEX portrait generation system from scratch.

#### **Prerequisites Check**
```bash
# Check if you're in the correct directory
pwd
# Should show: /home/aladine/Bureau/marouane/APEX/backend

# Verify Python is installed
python3 --version
# Should show Python 3.8 or higher

# Check if Node.js is installed (for frontend)
node --version
npm --version
```

#### **Step 1: Install and Start MongoDB**
```bash
# If MongoDB not installed yet, run installation commands:
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB service
sudo systemctl start mongod
sudo systemctl enable mongod

# Verify MongoDB is running
sudo systemctl status mongod
# Should show "active (running)"

# Test MongoDB connection
mongosh --eval "db.runCommand('ping')"
# Should return: { ok: 1 }
```

#### **Step 2: Install Python Dependencies**
```bash
# Navigate to backend directory
cd ~/Bureau/marouane/APEX/backend/job_manager

# Install required Python packages
pip install fastapi uvicorn pymongo python-multipart

# Or if using conda:
conda install fastapi uvicorn pymongo
pip install python-multipart

# Verify installations
python -c "import fastapi, uvicorn, pymongo; print('All dependencies installed successfully')"
```

#### **Step 3: Create Required Directories**
```bash
# Make sure you're in the job_manager directory
cd ~/Bureau/marouane/APEX/backend/job_manager

# Create uploads directory for reference photos
mkdir -p uploads
mkdir -p generated

# Set proper permissions
chmod 755 uploads
chmod 755 generated

# Verify directories exist
ls -la
# Should show uploads/ and generated/ directories
```

#### **Step 4: Start the Job Manager (Backend)**
```bash
# Navigate to job manager directory
cd ~/Bureau/marouane/APEX/backend/job_manager

# Start the FastAPI server
python main.py

# You should see output like:
# INFO:     Started server process [xxxxx]
# INFO:     Waiting for application startup.
# MongoDB connected successfully
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000

# Leave this terminal running - don't close it!
```

#### **Step 5: Test the Backend (New Terminal)**
```bash
# Open a new terminal (Ctrl+Shift+T)

# Test if the server is running
curl http://localhost:8000/

# Test the dashboard (should return HTML)
curl http://localhost:8000/dashboard

# Test API endpoints
curl http://localhost:8000/jobs
curl http://localhost:8000/stats

# Expected responses:
# Root: {"message": "APEX Job Manager API", "status": "running"}
# Jobs: {"jobs": []}
# Stats: {"total_jobs": 0, "pending": 0, "processing": 0, "completed": 0, "failed": 0}
```

#### **Step 6: Access the Web Dashboard**
```bash
# Open your web browser and go to:
http://localhost:8000/dashboard

# You should see:
# - APEX Job Manager Dashboard
# - Statistics panel showing 0 jobs
# - Empty jobs list
# - Auto-refresh every 30 seconds

# If you get connection refused, check Step 4 terminal for errors
```

#### **Step 7: Start the Frontend (Optional but Recommended)**
```bash
# Open a new terminal
cd ~/Bureau/marouane/APEX/web-app

# Install frontend dependencies (first time only)
npm install

# Start the React development server
npm run dev

# You should see:
# > vite dev
# > 
# > Local:   http://localhost:5173/
# > Network: use --host to expose

# Open browser to: http://localhost:5173/
# You should see the portrait generation form
```

#### **Step 8: Start vLLM Client (Optional - for AI Processing)**
```bash
# Open another new terminal
cd ~/Bureau/marouane/APEX/backend/job_manager

# Start the vLLM polling client
python vllm_client.py

# You should see:
# Starting vLLM Job Processor...
# Polling for jobs every 5 seconds...
# No pending jobs found.

# This will continuously poll for new jobs to process
# Leave this running if you want automatic job processing
```

#### **Step 9: Test Complete Workflow**

**Option A: Using Frontend (Recommended)**
```bash
# 1. Go to http://localhost:5173/ in your browser
# 2. Fill out the form:
#    - Purpose: LinkedIn
#    - Attire: Business Formal
#    - Background: Corporate Office
#    - Upload a reference photo
# 3. Click "Generate Portrait"
# 4. Note the job_id returned
# 5. Check dashboard: http://localhost:8000/dashboard
# 6. You should see your job listed
```

**Option B: Using API directly**
```bash
# Create a test job without file upload
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose": "LinkedIn",
    "attire": "Business Formal", 
    "background": "Corporate Office",
    "vibe": "Confident",
    "lighting": "Professional Flash",
    "mood": "Professional"
  }'

# Check the dashboard to see your new job
```

#### **Step 10: Monitor Everything**

**Terminal Layout Recommendation:**
```
Terminal 1: Job Manager (python main.py)
Terminal 2: Frontend (npm run dev) 
Terminal 3: vLLM Client (python vllm_client.py)
Terminal 4: Monitoring commands
```

**Monitoring Commands (Terminal 4):**
```bash
# Watch job status in real-time
watch -n 5 curl -s http://localhost:8000/stats

# Monitor MongoDB
mongosh --eval "use apex_database; db.jobs.find().count()"

# Check uploads directory
ls -la ~/Bureau/marouane/APEX/backend/job_manager/uploads/

# Monitor server logs (from job manager terminal)
# Look for lines like:
# INFO: New job created: abc-123
# INFO: Job status updated: abc-123 -> processing
```

### **🔧 Common Startup Issues and Solutions**

#### **Issue: MongoDB connection failed**
```bash
# Solution 1: Start MongoDB
sudo systemctl start mongod

# Solution 2: Check if port is in use
sudo netstat -tlnp | grep 27017

# Solution 3: Check MongoDB logs
sudo journalctl -u mongod
```

#### **Issue: Port 8000 already in use**
```bash
# Find what's using the port
sudo netstat -tlnp | grep 8000

# Kill the process
sudo fuser -k 8000/tcp

# Or run on different port
uvicorn main:app --host 0.0.0.0 --port 8001
```

#### **Issue: Python module not found**
```bash
# Install missing modules
pip install fastapi uvicorn pymongo python-multipart

# Or create virtual environment
python -m venv apex_env
source apex_env/bin/activate
pip install -r requirements.txt
```

#### **Issue: Frontend won't start**
```bash
# Install Node.js if missing
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### **📊 Verify Everything is Working**

Run this comprehensive check:
```bash
# 1. Check MongoDB
mongosh --eval "db.runCommand('ping')" && echo "✅ MongoDB OK"

# 2. Check Job Manager
curl -s http://localhost:8000/ | grep -q "running" && echo "✅ Job Manager OK"

# 3. Check Dashboard
curl -s http://localhost:8000/dashboard | grep -q "APEX" && echo "✅ Dashboard OK"

# 4. Check Frontend (if running)
curl -s http://localhost:5173/ | grep -q "html" && echo "✅ Frontend OK"

# 5. Check file permissions
[ -w uploads/ ] && echo "✅ Uploads directory writable"

# If all show ✅, your system is ready!
```

### **🎯 Quick Commands Summary**

```bash
# Start everything in the correct order:
sudo systemctl start mongod                    # 1. Start MongoDB
cd ~/Bureau/marouane/APEX/backend/job_manager  # 2. Go to backend
python main.py                                 # 3. Start Job Manager (Terminal 1)

# In new terminals:
cd ~/Bureau/marouane/APEX/web-app && npm run dev    # 4. Start Frontend (Terminal 2)
cd ~/Bureau/marouane/APEX/backend/job_manager && python vllm_client.py  # 5. Start vLLM Client (Terminal 3)

# Access points:
# Dashboard: http://localhost:8000/dashboard
# Frontend:  http://localhost:5173/
# API Docs:  http://localhost:8000/docs
```

---

## 🗄️ Database Setup

### **MongoDB Installation & Configuration**

```bash
# Install MongoDB GPG Key
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Add MongoDB Repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Start and Enable MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Check Status
sudo systemctl status mongod
```

### **Database Structure**

**Database Name:** `apex_database`

**Collections:**
- **`jobs`** - Complete job processing records
- **`profiles`** - User preference data only

**Job Record Schema:**
```json
{
  "job_id": "uuid-string",
  "prompt": "Generated AI prompt text",
  "style": "1024x1024 (Standard)",
  "seed": null,
  "status": "pending|processing|completed|failed",
  "image_url": "http://localhost:8000/generated/job_id.png",
  "reference_photo_url": "http://localhost:8000/uploads/job_id_reference.jpg",
  "reference_photo_path": "uploads/job_id_reference.jpg",
  "profile_data": { /* Complete form data */ },
  "created_at": "2025-07-25T10:00:00.000Z",
  "updated_at": "2025-07-25T10:05:30.000Z",
  "error_message": "Optional error details"
}
```

**Profile Record Schema:**
```json
{
  "job_id": "uuid-string",
  "profile_data": {
    "basic_info": {
      "purpose": "LinkedIn",
      "attire": "Business Formal",
      "background": "Corporate Office",
      "vibe": "Confident"
    },
    "advanced_settings": {
      "lighting": "Professional Flash",
      "mood": "Professional",
      "age_range": "30-40",
      "gender": "Female",
      "ethnicity": "Middle Eastern",
      "resolution": "1024x1024 (Standard)"
    },
    "additional_info": {
      "reference_photo": "filename.jpg",
      "custom_notes": "Specific requirements",
      "preset_used": "LinkedIn Professional"
    },
    "metadata": {
      "timestamp": "2025-07-25 10:00:00",
      "version": "2.0",
      "created_by": "APEX Portrait Generator (Web)"
    },
    "generated_prompt": "Complete AI-optimized prompt..."
  },
  "created_at": "2025-07-25T10:00:00.000Z"
}
```

---

## 🔍 MongoDB Access Methods

### **1. Built-in Web Dashboard (Recommended)**
```bash
# Start the Job Manager server
cd ~/Bureau/marouane/APEX/backend/job_manager
python main.py

# Access dashboard in browser
http://localhost:8000/dashboard
```

**Features:**
- 📊 Real-time statistics
- 📋 Job listings with expandable details
- 📸 Direct links to reference photos
- 🔄 Auto-refresh every 30 seconds
- 📱 Mobile responsive

### **2. MongoDB Shell (mongosh)**
```bash
# Connect to MongoDB
mongosh

# Switch to database
use apex_database

# View collections
show collections

# View all jobs
db.jobs.find().pretty()

# View all profiles
db.profiles.find().pretty()

# Count documents
db.jobs.countDocuments()
db.profiles.countDocuments()

# Find specific job
db.jobs.findOne({"job_id": "your-job-id-here"})

# Find pending jobs
db.jobs.find({"status": "pending"}).pretty()

# Find jobs with photos
db.jobs.find({"reference_photo_url": {"$ne": null}}).pretty()

# Sort by creation date (newest first)
db.jobs.find().sort({"created_at": -1}).limit(10).pretty()

# Find jobs by status
db.jobs.find({"status": "completed"}).pretty()

# Get statistics
db.jobs.aggregate([
  {"$group": {"_id": "$status", "count": {"$sum": 1}}}
])

# Exit mongosh
exit
```

### **3. FastAPI Interactive Documentation**
```
http://localhost:8000/docs
```

### **4. MongoDB Compass (GUI)**
```bash
# Install MongoDB Compass
sudo snap install mongodb-compass

# Launch
mongodb-compass

# Connection String: mongodb://localhost:27017
# Database: apex_database
# Collections: jobs, profiles
```

### **5. VS Code Extension**
1. Install "MongoDB for VS Code" extension
2. Connect to: `mongodb://localhost:27017`
3. Browse database directly in VS Code

---

## 💾 Data Export/Import

### **Export Data**

#### **Method 1: Using mongoexport (Command Line)**
```bash
# Export all jobs to JSON
mongoexport --db apex_database --collection jobs --out apex_jobs_export.json --pretty

# Export all profiles to JSON
mongoexport --db apex_database --collection profiles --out apex_profiles_export.json --pretty

# Export with query filter (e.g., completed jobs only)
mongoexport --db apex_database --collection jobs --query '{"status": "completed"}' --out completed_jobs.json --pretty

# Export recent jobs (last 24 hours)
mongoexport --db apex_database --collection jobs --query '{"created_at": {"$gte": {"$date": "2025-07-25T00:00:00.000Z"}}}' --out recent_jobs.json --pretty
```

#### **Method 2: Using Built-in API Endpoints**
```bash
# Make sure server is running first
python main.py

# Export all data
curl http://localhost:8000/export/all > complete_apex_export.json

# Export jobs only
curl http://localhost:8000/export/jobs > jobs_only_export.json

# Export profiles only
curl http://localhost:8000/export/profiles > profiles_only_export.json

# Export current statistics
curl http://localhost:8000/stats > current_stats.json
```

#### **Method 3: Using Python Export Script**
```bash
# Run the provided export script
python export_data.py

# This creates:
# - apex_jobs_export.json
# - apex_profiles_export.json  
# - apex_complete_export.json
```

#### **Method 4: Full Database Backup**
```bash
# Create complete binary backup
mongodump --db apex_database --out backup_$(date +%Y%m%d_%H%M%S)

# This creates a complete backup including indexes
```

### **Import Data**

#### **Restore from JSON exports**
```bash
# Import jobs
mongoimport --db apex_database --collection jobs --file apex_jobs_export.json

# Import profiles
mongoimport --db apex_database --collection profiles --file apex_profiles_export.json

# Import with upsert (update existing, insert new)
mongoimport --db apex_database --collection jobs --file apex_jobs_export.json --upsert --upsertFields job_id
```

#### **Restore from binary backup**
```bash
# Restore complete database
mongorestore --db apex_database backup_folder/apex_database/

# Drop existing data and restore
mongorestore --drop --db apex_database backup_folder/apex_database/
```

### **Transfer Files (Reference Photos)**
```bash
# Create archive of uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/

# Extract on destination server
tar -xzf uploads_backup_20250725.tar.gz
```

---

## 🤖 vLLM Independent Server Integration

### **Architecture Overview**
```
Frontend → Job Manager → MongoDB ← vLLM Server (polls)
```

### **How It Works**

#### **Step 1: Job Submission**
1. User submits form via frontend
2. Job Manager receives data and creates job with `status: "pending"`
3. Job stored in MongoDB with unique `job_id`
4. User receives `job_id` for tracking

#### **Step 2: vLLM Server Polling**
1. vLLM server runs continuous polling loop
2. Calls `GET /jobs/pending` every 5 seconds
3. Receives list of jobs with `status: "pending"`
4. Processes jobs one by one

#### **Step 3: Job Processing**
1. vLLM server claims job: `PUT /jobs/{job_id}/status?status=processing`
2. Calls actual vLLM API with prompt and reference photo
3. Generates image and gets result URL
4. Updates job: `PUT /jobs/{job_id}/status?status=completed&image_url=...`

#### **Step 4: Result Display**
1. User checks dashboard or frontend
2. Sees updated job status and generated image
3. Can download or view the result

### **vLLM Server Implementation**

#### **Basic Polling Client (vllm_client.py)**
```python
import requests
import time

class VLLMJobProcessor:
    def __init__(self, job_manager_url="http://localhost:8000"):
        self.job_manager_url = job_manager_url
    
    def poll_for_jobs(self):
        while True:
            try:
                # Get pending jobs
                response = requests.get(f"{self.job_manager_url}/jobs/pending")
                pending_jobs = response.json().get("pending_jobs", [])
                
                for job in pending_jobs:
                    self.process_job(job)
                    
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)
    
    def process_job(self, job):
        job_id = job["job_id"]
        
        # 1. Claim job
        self.update_status(job_id, "processing")
        
        # 2. Call vLLM (replace with actual vLLM call)
        result = self.call_vllm(job["prompt"], job.get("reference_photo_url"))
        
        # 3. Update with results
        if result["success"]:
            self.update_status(job_id, "completed", result["image_url"])
        else:
            self.update_status(job_id, "failed", error_message=result["error"])
    
    def update_status(self, job_id, status, image_url=None, error_message=None):
        params = {"status": status}
        if image_url:
            params["image_url"] = image_url
        if error_message:
            params["error_message"] = error_message
            
        requests.put(f"{self.job_manager_url}/jobs/{job_id}/status", params=params)

# Run the processor
if __name__ == "__main__":
    processor = VLLMJobProcessor()
    processor.poll_for_jobs()
```

#### **Running vLLM Integration**
```bash
# Terminal 1: Start Job Manager
cd ~/Bureau/marouane/APEX/backend/job_manager
python main.py

# Terminal 2: Start vLLM Client
python vllm_client.py

# Terminal 3: Start Frontend (optional)
cd ~/Bureau/marouane/APEX/web-app
npm run dev
```

### **Scalability: Multiple vLLM Workers**
```bash
# Run multiple instances for parallel processing
python vllm_client.py &  # Worker 1
python vllm_client.py &  # Worker 2
python vllm_client.py &  # Worker 3

# Each worker will claim different jobs automatically
```

---

## 🌐 API Endpoints

### **Job Management**
```bash
# Get all jobs
GET /jobs
curl http://localhost:8000/jobs

# Get specific job
GET /jobs/{job_id}
curl http://localhost:8000/jobs/abc-123

# Create new job (FormData with file upload)
POST /jobs
# (Used by frontend form submission)

# Delete job
DELETE /jobs/{job_id}
curl -X DELETE http://localhost:8000/jobs/abc-123
```

### **Profile Management**
```bash
# Get all profiles
GET /profiles
curl http://localhost:8000/profiles

# Get specific profile
GET /profiles/{job_id}
curl http://localhost:8000/profiles/abc-123
```

### **vLLM Integration Endpoints**
```bash
# Get pending jobs (for vLLM server)
GET /jobs/pending
curl http://localhost:8000/jobs/pending

# Get processing jobs
GET /jobs/processing
curl http://localhost:8000/jobs/processing

# Update job status (for vLLM server)
PUT /jobs/{job_id}/status
curl -X PUT "http://localhost:8000/jobs/abc-123/status?status=completed&image_url=http://..."
```

### **Data Export Endpoints**
```bash
# Export all data
GET /export/all
curl http://localhost:8000/export/all > complete_export.json

# Export jobs only
GET /export/jobs
curl http://localhost:8000/export/jobs > jobs_export.json

# Export profiles only
GET /export/profiles
curl http://localhost:8000/export/profiles > profiles_export.json
```

### **System Information**
```bash
# Get system statistics
GET /stats
curl http://localhost:8000/stats

# Web dashboard
GET /dashboard
# Visit: http://localhost:8000/dashboard

# API documentation
GET /docs
# Visit: http://localhost:8000/docs
```

---

## 🔧 Troubleshooting

### **MongoDB Issues**

#### **MongoDB not starting**
```bash
# Check MongoDB status
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod

# Check MongoDB logs
sudo journalctl -u mongod

# Check if port is in use
sudo netstat -tlnp | grep 27017
```

#### **Connection refused**
```bash
# Check if MongoDB is running
mongosh --eval "db.runCommand('ping')"

# Check configuration file
cat /etc/mongod.conf

# Restart MongoDB
sudo systemctl restart mongod
```

#### **Permission issues**
```bash
# Fix MongoDB permissions
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo chown -R mongodb:mongodb /var/log/mongodb
sudo systemctl restart mongod
```

### **Job Manager Issues**

#### **PyMongo import error**
```bash
# Install PyMongo
pip install pymongo

# Or in conda environment
conda install pymongo
```

#### **Upload directory issues**
```bash
# Check if uploads directory exists
ls -la uploads/

# Create if missing
mkdir -p uploads/
chmod 755 uploads/
```

#### **Port conflicts**
```bash
# Check if port 8000 is in use
sudo netstat -tlnp | grep 8000

# Kill process using port
sudo fuser -k 8000/tcp
```

### **vLLM Integration Issues**

#### **Jobs stuck in processing**
```bash
# Check for jobs stuck in processing state
mongosh
use apex_database
db.jobs.find({"status": "processing"}).pretty()

# Reset stuck jobs to pending
db.jobs.updateMany(
  {"status": "processing", "updated_at": {"$lt": new Date(Date.now() - 300000)}},
  {"$set": {"status": "pending"}}
)
```

#### **vLLM client not processing jobs**
```bash
# Check if vLLM client is running
ps aux | grep vllm_client

# Check vLLM client logs
python vllm_client.py  # Run in foreground to see logs

# Test manual API calls
curl http://localhost:8000/jobs/pending
```

### **Data Export Issues**

#### **mongoexport not found**
```bash
# Install MongoDB database tools
sudo apt install mongodb-database-tools

# Or using snap
sudo snap install mongodb-database-tools
```

#### **Export permissions**
```bash
# Ensure write permissions
chmod 755 .
ls -la *.json
```

---

## 📊 Database Monitoring

### **Real-time Monitoring Commands**
```bash
# Watch job status changes
mongosh --eval "
use apex_database;
while(true) {
  print('=== Job Status Summary ===');
  db.jobs.aggregate([{\$group: {_id: '\$status', count: {\$sum: 1}}}]).forEach(printjson);
  print('');
  sleep(5000);
}
"

# Monitor database size
mongosh --eval "db.stats()" apex_database

# Watch MongoDB logs in real-time
sudo tail -f /var/log/mongodb/mongod.log
```

### **Performance Optimization**
```bash
# Create indexes for better query performance
mongosh apex_database --eval "
db.jobs.createIndex({'job_id': 1});
db.jobs.createIndex({'status': 1});
db.jobs.createIndex({'created_at': -1});
db.profiles.createIndex({'job_id': 1});
"
```

---

## 🚀 Quick Start Checklist

1. **✅ Install MongoDB** - Follow installation steps above
2. **✅ Start MongoDB** - `sudo systemctl start mongod`
3. **✅ Install Python dependencies** - `pip install pymongo fastapi uvicorn`
4. **✅ Start Job Manager** - `python main.py`
5. **✅ Test dashboard** - Visit `http://localhost:8000/dashboard`
6. **✅ Start vLLM client** - `python vllm_client.py` (optional)
7. **✅ Start frontend** - `npm run dev` in web-app directory
8. **✅ Submit test job** - Use frontend form
9. **✅ Check database** - Use mongosh or dashboard
10. **✅ Export data** - Use API endpoints or mongoexport

---

## 📞 Support

For issues with this setup:
1. Check the troubleshooting section above
2. Verify all services are running: `sudo systemctl status mongod`
3. Check logs: Job Manager terminal output and MongoDB logs
4. Test API endpoints manually with curl
5. Use the built-in dashboard for real-time monitoring

**Last Updated:** July 25, 2025  
**System:** Ubuntu Linux with MongoDB 7.0, Python 3.x, FastAPI
