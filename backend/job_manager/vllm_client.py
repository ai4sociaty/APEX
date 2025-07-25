#!/usr/bin/env python3
"""
vLLM Independent Server Client
This shows how your vLLM server would poll for jobs and process them
"""

import requests
import time
import json
from datetime import datetime

class VLLMJobProcessor:
    def __init__(self, job_manager_url="http://localhost:8000", vllm_url="http://localhost:8001"):
        self.job_manager_url = job_manager_url
        self.vllm_url = vllm_url
        self.processing = False
        
    def poll_for_jobs(self):
        """Main polling loop - run this continuously"""
        print("🚀 vLLM Job Processor started")
        print(f"📡 Polling Job Manager at: {self.job_manager_url}")
        print(f"🤖 vLLM Server at: {self.vllm_url}")
        
        while True:
            try:
                self.check_and_process_jobs()
                time.sleep(5)  # Poll every 5 seconds
            except KeyboardInterrupt:
                print("\n🛑 Stopping vLLM Job Processor")
                break
            except Exception as e:
                print(f"❌ Error in polling loop: {e}")
                time.sleep(10)  # Wait longer on error
    
    def check_and_process_jobs(self):
        """Check for pending jobs and process them"""
        try:
            # Get pending jobs from Job Manager
            response = requests.get(f"{self.job_manager_url}/jobs/pending")
            if response.status_code != 200:
                print(f"❌ Failed to get pending jobs: {response.status_code}")
                return
                
            data = response.json()
            pending_jobs = data.get("pending_jobs", [])
            
            if pending_jobs:
                print(f"📋 Found {len(pending_jobs)} pending jobs")
                
                for job in pending_jobs:
                    self.process_job(job)
            else:
                print("💤 No pending jobs")
                
        except Exception as e:
            print(f"❌ Error checking for jobs: {e}")
    
    def process_job(self, job):
        """Process a single job"""
        job_id = job["job_id"]
        prompt = job["prompt"]
        
        print(f"\n🔄 Processing job: {job_id}")
        print(f"📝 Prompt: {prompt[:100]}...")
        
        try:
            # 1. Update status to processing
            self.update_job_status(job_id, "processing")
            
            # 2. Call vLLM server (or simulate processing)
            result = self.call_vllm_server(prompt, job)
            
            # 3. Update status to completed with results
            if result["success"]:
                self.update_job_status(
                    job_id, 
                    "completed", 
                    image_url=result.get("image_url")
                )
                print(f"✅ Job {job_id} completed successfully")
            else:
                self.update_job_status(
                    job_id, 
                    "failed", 
                    error_message=result.get("error")
                )
                print(f"❌ Job {job_id} failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error processing job {job_id}: {e}")
            self.update_job_status(job_id, "failed", error_message=str(e))
    
    def call_vllm_server(self, prompt, job):
        """Call the actual vLLM server (or simulate it)"""
        try:
            # TODO: Replace this with actual vLLM API call
            # For now, simulate processing
            print("🤖 Calling vLLM server...")
            time.sleep(2)  # Simulate processing time
            
            # Simulated success
            return {
                "success": True,
                "image_url": f"http://localhost:8000/generated/{job['job_id']}.png",
                "processing_time": 2.0
            }
            
            # Real vLLM call would look like:
            # response = requests.post(f"{self.vllm_url}/generate", {
            #     "prompt": prompt,
            #     "max_tokens": 100,
            #     "temperature": 0.7
            # })
            # 
            # if response.status_code == 200:
            #     return {"success": True, "image_url": response.json()["image_url"]}
            # else:
            #     return {"success": False, "error": f"vLLM error: {response.status_code}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_job_status(self, job_id, status, image_url=None, error_message=None):
        """Update job status in Job Manager"""
        try:
            data = {"status": status}
            if image_url:
                data["image_url"] = image_url
            if error_message:
                data["error_message"] = error_message
                
            response = requests.put(
                f"{self.job_manager_url}/jobs/{job_id}/status",
                params=data
            )
            
            if response.status_code == 200:
                print(f"📊 Updated job {job_id} status to: {status}")
            else:
                print(f"❌ Failed to update job status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error updating job status: {e}")

if __name__ == "__main__":
    processor = VLLMJobProcessor()
    processor.poll_for_jobs()
