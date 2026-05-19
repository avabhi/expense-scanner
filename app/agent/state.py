from typing import TypedDict, Optional
from app.schemas.receipt import ReceiptSchema

class AgentState(TypedDict):
    image_url: str
    raw_extraction: Optional[dict]
    validated_receipt: Optional[ReceiptSchema]
    errors: list[str]
