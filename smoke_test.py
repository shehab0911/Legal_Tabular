import requests
import os
import sys
import time

# Usage:
# 1. Ensure the system is running (Docker Compose).
# 2. Run this script: python qa_smoke_test.py
#    (Requires 'requests' library: pip install requests)
#
# Note: If running inside Docker container, set API_URL environment variable:
#       export API_URL="http://localhost:8000"

BASE_URL = os.getenv("API_URL", "http://localhost:8002")

def log(msg):
    print(f"[SMOKE TEST] {msg}")

def test_health():
    log("Checking health...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            log(f"Health check passed: {resp.json()}")
            return True
        else:
            log(f"Health check failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        log(f"Health check exception: {e}")
        return False

def test_create_project():
    log("Creating project...")
    payload = {
        "name": "Smoke Test Project",
        "description": "Created by QA smoke test script"
    }
    resp = requests.post(f"{BASE_URL}/projects", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        project_id = data.get("id")
        log(f"Project created: {project_id}")
        return project_id
    else:
        log(f"Failed to create project: {resp.status_code} - {resp.text}")
        return None

def test_upload_document(project_id, file_path):
    log(f"Uploading document: {file_path}")
    if not os.path.exists(file_path):
        log(f"File not found: {file_path}")
        return False
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{BASE_URL}/projects/{project_id}/documents/upload", files=files)
        
    if resp.status_code == 200:
        data = resp.json()
        doc_id = data.get("id")
        log(f"Document uploaded: {doc_id}")
        return doc_id
    else:
        log(f"Failed to upload document: {resp.status_code} - {resp.text}")
        return None

def test_check_document_status(project_id, doc_id):
    log(f"Checking document status: {doc_id}")
    # Give it a moment to process
    time.sleep(2)
    resp = requests.get(f"{BASE_URL}/projects/{project_id}/documents")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            documents = data
        else:
            documents = data.get("items", data.get("documents", []))
            
        for doc in documents:
            if doc.get("id") == doc_id:
                status = doc.get("status")
                log(f"Document status: {status}")
                return status
        log(f"Document not found in list. Response: {data}")
        return None
    else:
        log(f"Failed to list documents: {resp.status_code} - {resp.text}")
        return None

def test_delete_project(project_id):
    log(f"Deleting project: {project_id}")
    resp = requests.delete(f"{BASE_URL}/projects/{project_id}")
    if resp.status_code == 200:
        log("Project deleted successfully")
        return True
    else:
        log(f"Failed to delete project: {resp.status_code} - {resp.text}")
        return False

def run_smoke_test():
    log("Starting QA Smoke Test...")
    
    if not test_health():
        log("Aborting: System is not healthy")
        sys.exit(1)
        
    project_id = test_create_project()
    if not project_id:
        log("Aborting: Could not create project")
        sys.exit(1)
        
    # Use absolute path to the data file
    data_file = os.path.abspath(os.path.join("data", "Supply Agreement.pdf"))
    
    doc_id = test_upload_document(project_id, data_file)
    
    if doc_id:
        status = test_check_document_status(project_id, doc_id)
        if status:
             log(f"Verified document status: {status}")
        else:
             log("Could not verify document status")
    
    # Even if upload fails, try to clean up
    if project_id:
        test_delete_project(project_id)
        
    if doc_id:
        log("Smoke Test COMPLETED SUCCESSFULLY")
    else:
        log("Smoke Test FAILED at document upload")
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()
