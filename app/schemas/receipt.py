from typing import List, Dict, Any
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str = Field(..., description="The name or description of the purchased item")
    price: float = Field(..., description="The cost of the item")

class ReceiptSchema(BaseModel):
    merchant_name: str = Field(..., description="Name of the store or merchant")
    date: str = Field(..., description="Date of the purchase in YYYY-MM-DD format")
    total_amount: float = Field(..., description="The total amount paid")
    currency: str = Field(..., description="The 3-letter currency code, e.g., USD, INR, EUR")
    line_items: List[LineItem] = Field(default_factory=list, description="List of items purchased")
