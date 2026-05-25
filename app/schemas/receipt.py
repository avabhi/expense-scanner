from typing import List, Literal
from pydantic import BaseModel, Field

# Fixed set of spending categories the LLM must choose from
ExpenseCategory = Literal[
    "Food & Dining",
    "Groceries",
    "Transport",
    "Health & Pharmacy",
    "Electronics & Tech",
    "Clothing & Apparel",
    "Entertainment",
    "Utilities & Bills",
    "Personal Care",
    "Other"
]

class LineItem(BaseModel):
    description: str = Field(..., description="The name or description of the purchased item")
    price: float = Field(..., description="The cost of the item")
    category: ExpenseCategory = Field(
        ...,
        description=(
            "Spending category for this item. Choose exactly one from: "
            "Food & Dining (restaurants, cafes, fast food), "
            "Groceries (supermarket items, vegetables, household staples, personal care products like shampoo), "
            "Transport (fuel, taxi, parking, public transit), "
            "Health & Pharmacy (medicines, doctor visits, hospital), "
            "Electronics & Tech (phones, laptops, accessories), "
            "Clothing & Apparel (clothes, shoes, fashion), "
            "Entertainment (movies, games, streaming, events), "
            "Utilities & Bills (electricity, internet, rent, phone bill), "
            "Personal Care (salon, haircut, spa, cosmetics), "
            "Other (anything that doesn't fit the above)."
        )
    )

class ReceiptSchema(BaseModel):
    merchant_name: str = Field(..., description="Name of the store or merchant")
    date: str = Field(..., description="Date of the purchase in YYYY-MM-DD format")
    total_amount: float = Field(..., description="The total amount paid")
    currency: str = Field(..., description="The 3-letter currency code, e.g., USD, INR, EUR")
    line_items: List[LineItem] = Field(default_factory=list, description="List of items purchased with their category")

