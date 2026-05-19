import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.cloud_storage import create_presigned_post
from app.worker.celery_app import celery_app

router = APIRouter()

class UploadUrlResponse(BaseModel):
    url: str
    fields: dict
    object_key: str

class ReceiptIngestRequest(BaseModel):
    object_key: str
    file_hash: str  # For idempotency

@router.get("/upload-url", response_model=UploadUrlResponse)
def get_upload_url(filename: str):
    """
    Generate a presigned URL to upload a receipt directly to S3.
    """
    # Create a unique object key to prevent overwrites
    object_key = f"receipts/{uuid.uuid4()}-{filename}"
    
    presigned = create_presigned_post(object_key)
    if not presigned:
        raise HTTPException(status_code=500, detail="Could not generate upload URL")
        
    return UploadUrlResponse(
        url=presigned["url"],
        fields=presigned["fields"],
        object_key=object_key
    )

@router.post("/", status_code=202)
def ingest_receipt(request: ReceiptIngestRequest):
    """
    Webhook / Notification that a receipt was uploaded.
    This enqueues the processing job.
    """
    # TODO: Check database if `file_hash` already exists (Idempotency)
    
    # Enqueue the Celery background task
    task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
    
    return {
        "message": "Receipt processing job accepted.",
        "job_id": task.id
    }
