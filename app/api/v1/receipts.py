import uuid
import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis.asyncio as aioredis

from app.core.cloud_storage import create_presigned_post
from app.worker.celery_app import celery_app
from app.api.deps import get_db
from app.models.receipt import Receipt
from app.core.config import settings

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
def ingest_receipt(request: ReceiptIngestRequest, db: Session = Depends(get_db)):
    """
    Webhook / Notification that a receipt was uploaded.
    Implements idempotency and enqueues the processing job.
    """
    # 1. Idempotency Check
    existing_receipt = db.query(Receipt).filter(Receipt.file_hash == request.file_hash).first()
    
    if existing_receipt:
        # If it was completed, we return the cached record
        if existing_receipt.status == "completed":
            return {
                "message": "Receipt already processed (Cached).",
                "status": existing_receipt.status,
                "receipt_id": str(existing_receipt.id),
                "merchant_name": existing_receipt.merchant_name,
                "total_amount": existing_receipt.total_amount
            }
        # If it's already processing/pending, return status
        elif existing_receipt.status in ["pending", "processing"]:
            return {
                "message": "Receipt is already being processed.",
                "status": existing_receipt.status,
                "receipt_id": str(existing_receipt.id)
            }
        # If it failed previously, we will re-attempt processing
        elif existing_receipt.status == "failed":
            existing_receipt.status = "pending"
            existing_receipt.s3_object_key = request.object_key
            db.commit()
            
            task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
            return {
                "message": "Re-attempting failed receipt processing.",
                "status": "pending",
                "receipt_id": str(existing_receipt.id),
                "job_id": task.id
            }

    # 2. Create a new Receipt record in the database
    new_receipt = Receipt(
        s3_object_key=request.object_key,
        file_hash=request.file_hash,
        status="pending"
    )
    db.add(new_receipt)
    db.commit()
    db.refresh(new_receipt)
    
    # 3. Enqueue the Celery background task
    task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
    
    return {
        "message": "Receipt processing job accepted.",
        "status": "pending",
        "receipt_id": str(new_receipt.id),
        "job_id": task.id
    }

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Server-Sent Events (SSE) endpoint to stream real-time task progress.
    """
    async def event_generator():
        r = aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"receipt_progress:{task_id}")
        
        try:
            # Yield initial connection confirmation
            yield f"data: {json.dumps({'status': 'connected', 'message': 'Subscribed to job updates.'})}\n\n"
            
            while True:
                # Poll Redis pubsub for messages
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = message['data'].decode('utf-8')
                    yield f"data: {data}\n\n"
                    
                    # If status is terminal (completed or failed), end stream
                    parsed_data = json.loads(data)
                    if parsed_data.get("status") in ["completed", "failed"]:
                        break
                
                await asyncio.sleep(0.2)
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        finally:
            await pubsub.unsubscribe(f"receipt_progress:{task_id}")
            await r.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
