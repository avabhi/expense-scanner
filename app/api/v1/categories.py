from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.receipt import Receipt, LineItem
from app.models.user import User

router = APIRouter()


@router.get("/summary")
def get_category_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns total spending grouped by expense category across all completed receipts
    for the current authenticated user.
    Each category includes the total amount spent, item count, and the list of
    receipts that contain items in that category (for user verification).
    """
    # Query all line items from completed receipts belonging to the user
    rows = (
        db.query(LineItem, Receipt)
        .join(Receipt, LineItem.receipt_id == Receipt.id)
        .filter(Receipt.status == "completed", Receipt.user_id == current_user.id)
        .all()
    )

    # Aggregate by category
    category_totals: dict[str, float] = defaultdict(float)
    category_item_counts: dict[str, int] = defaultdict(int)
    # Map category -> set of receipt IDs seen
    category_receipts: dict[str, dict[str, dict]] = defaultdict(dict)

    for line_item, receipt in rows:
        cat = line_item.category or "Other"
        receipt_id = str(receipt.id)

        category_totals[cat] += line_item.price
        category_item_counts[cat] += 1

        # Only store unique receipts per category
        if receipt_id not in category_receipts[cat]:
            category_receipts[cat][receipt_id] = {
                "receipt_id": receipt_id,
                "merchant_name": receipt.merchant_name,
                "date": receipt.date.isoformat() if receipt.date else None,
                "total_amount": receipt.total_amount,
                "currency": receipt.currency,
            }

    # Build the response list, sorted by total spent descending
    result = []
    for category, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        result.append({
            "category": category,
            "total_spent": round(total, 2),
            "item_count": category_item_counts[category],
            "receipts": list(category_receipts[category].values()),
        })

    return result


@router.get("/list")
def get_all_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all distinct categories that have been assigned to line items
    for the current authenticated user.
    """
    categories = (
        db.query(LineItem.category)
        .join(Receipt, LineItem.receipt_id == Receipt.id)
        .filter(
            Receipt.status == "completed",
            Receipt.user_id == current_user.id,
            LineItem.category.isnot(None)
        )
        .distinct()
        .all()
    )
    return {"categories": [c[0] for c in categories if c[0]]}
