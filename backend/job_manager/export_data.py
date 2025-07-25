
"""
Quick script to export MongoDB data to JSON files
"""

from pymongo import MongoClient
import json
from datetime import datetime

def export_to_json():
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client.apex_database
        
        # Get collections
        jobs_collection = db.jobs
        profiles_collection = db.profiles
        
        # Export jobs
        jobs = list(jobs_collection.find({}, {"_id": 0}))
        with open("apex_jobs_export.json", "w") as f:
            json.dump(jobs, f, indent=2, default=str)
        
        # Export profiles  
        profiles = list(profiles_collection.find({}, {"_id": 0}))
        with open("apex_profiles_export.json", "w") as f:
            json.dump(profiles, f, indent=2, default=str)
        
        # Export combined data
        combined_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_jobs": len(jobs),
            "total_profiles": len(profiles),
            "jobs": jobs,
            "profiles": profiles
        }
        
        with open("apex_complete_export.json", "w") as f:
            json.dump(combined_data, f, indent=2, default=str)
        
        print(f"✅ Export completed!")
        print(f"📄 Jobs exported: {len(jobs)} → apex_jobs_export.json")
        print(f"📄 Profiles exported: {len(profiles)} → apex_profiles_export.json") 
        print(f"📄 Complete export: → apex_complete_export.json")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

if __name__ == "__main__":
    export_to_json()
