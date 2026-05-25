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
from app.api.deps import get_db, get_current_user
from app.models.receipt import Receipt
from app.models.user import User
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
def get_upload_url(filename: str, current_user: User = Depends(get_current_user)):
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

@router.post("", status_code=202)
def ingest_receipt(
    request: ReceiptIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Webhook / Notification that a receipt was uploaded.
    Implements idempotency and enqueues the processing job.
    """
    import redis
    r = redis.Redis.from_url(settings.REDIS_URL)
    task_id_key = f"receipt_task:{current_user.id}:{request.file_hash}"

    # 1. Idempotency Check
    existing_receipt = db.query(Receipt).filter(
        Receipt.file_hash == request.file_hash,
        Receipt.user_id == current_user.id
    ).first()
    
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
            existing_task_id = r.get(task_id_key)
            if existing_task_id:
                job_id = existing_task_id.decode("utf-8")
            else:
                # Trigger a new task to resume processing since no active task is tracked
                task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
                job_id = task.id
                r.setex(task_id_key, 86400, job_id)
                
            return {
                "message": "Receipt is already being processed.",
                "status": existing_receipt.status,
                "receipt_id": str(existing_receipt.id),
                "job_id": job_id
            }
        # If it failed previously, we will re-attempt processing
        elif existing_receipt.status == "failed":
            existing_receipt.status = "pending"
            existing_receipt.s3_object_key = request.object_key
            db.commit()
            
            task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
            r.setex(task_id_key, 86400, task.id)
            
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
        status="pending",
        user_id=current_user.id
    )
    db.add(new_receipt)
    db.commit()
    db.refresh(new_receipt)
    
    # 3. Enqueue the Celery background task
    task = celery_app.send_task("app.worker.tasks.process_receipt", args=[request.object_key])
    r.setex(task_id_key, 86400, task.id)
    
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

@router.get("/{receipt_id}")
def get_receipt(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the details of a processed receipt including line items.
    """
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid receipt ID format")

    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_uuid,
        Receipt.user_id == current_user.id
    ).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    return {
        "id": str(receipt.id),
        "merchant_name": receipt.merchant_name,
        "date": receipt.date.isoformat() if receipt.date else None,
        "total_amount": receipt.total_amount,
        "currency": receipt.currency,
        "status": receipt.status,
        "line_items": [
            {
                "id": item.id,
                "description": item.description,
                "price": item.price,
                "category": item.category,
            }
            for item in receipt.line_items
        ]
    }

