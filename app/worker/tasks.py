import json
import redis
from celery import current_task
from datetime import datetime

from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.receipt import Receipt, LineItem
from app.core.config import settings
from app.core.cloud_storage import get_presigned_download_url
from app.agent.graph import receipt_graph

def publish_progress(task_id: str, status: str, step: str, message: str):
    """
    Publish progress updates to Redis Pub/Sub for SSE streaming.
    """
    r = redis.Redis.from_url(settings.REDIS_URL)
    r.publish(
        f"receipt_progress:{task_id}",
        json.dumps({
            "task_id": task_id,
            "status": status,
            "step": step,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    )

@celery_app.task(name="app.worker.tasks.process_receipt", bind=True)
def process_receipt(self, object_key: str):
    task_id = self.request.id
    db = SessionLocal()
    
    try:
        # 1. Update status to processing in DB
        receipt = db.query(Receipt).filter(Receipt.s3_object_key == object_key).first()
        if not receipt:
            publish_progress(task_id, "failed", "db_lookup", "Receipt record not found in database.")
            return {"error": "Receipt record not found"}
            
        receipt.status = "processing"
        db.commit()
        
        publish_progress(task_id, "processing", "start", "Generating secure link to access receipt image...")
        
        # 2. Generate secure temporary download URL for OpenAI Vision
        download_url = get_presigned_download_url(object_key)
        if not download_url:
            receipt.status = "failed"
            db.commit()
            publish_progress(task_id, "failed", "presigned_url", "Failed to generate access link for image.")
            return {"error": "Failed to generate presigned URL"}
            
        publish_progress(task_id, "processing", "agent_start", "Vision AI starting extraction...")
        
        # 3. Invoke LangGraph agent
        state_input = {
            "image_url": download_url,
            "raw_extraction": None,
            "validated_receipt": None,
            "errors": []
        }
        
        # Run graph
        result = receipt_graph.invoke(state_input)
        
        # Check for errors in state
        if result.get("errors"):
            receipt.status = "failed"
            db.commit()
            error_msg = result["errors"][0]
            publish_progress(task_id, "failed", "agent_failure", f"AI processing failed: {error_msg}")
            return {"error": error_msg}
            
        validated = result.get("validated_receipt")
        if not validated:
            receipt.status = "failed"
            db.commit()
            publish_progress(task_id, "failed", "agent_failure", "AI finished but no receipt data was extracted.")
            return {"error": "No receipt data extracted"}
            
        publish_progress(task_id, "processing", "saving", "AI extraction successful. Saving data...")
        
        # 4. Save results to PostgreSQL
        receipt.merchant_name = validated.merchant_name
        
        # Parse date cleanly if possible
        try:
            receipt.date = datetime.strptime(validated.date, "%Y-%m-%d").date()
        except Exception:
            receipt.date = None  # Fallback if AI returned invalid date format
            
        receipt.total_amount = validated.total_amount
        receipt.currency = validated.currency
        receipt.status = "completed"
        
        # Clear existing line items if any (should be none since status was pending)
        receipt.line_items.clear()
        
        # Add new line items
        for item in validated.line_items:
            line_item = LineItem(
                # pyrefly: ignore [unexpected-keyword]
                description=item.description,
                # pyrefly: ignore [unexpected-keyword]
                price=item.price
            )
            receipt.line_items.append(line_item)
            
        db.commit()
        publish_progress(task_id, "completed", "done", "Receipt processed successfully!")
        
        return {
            "status": "completed",
            "merchant_name": receipt.merchant_name,
            "total_amount": receipt.total_amount
        }
        
    except Exception as e:
        db.rollback()
        if 'receipt' in locals() and receipt:
            receipt.status = "failed"
            db.commit()
        publish_progress(task_id, "failed", "system_error", f"System error occurred: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()
