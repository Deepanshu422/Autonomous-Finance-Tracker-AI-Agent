from pydantic import BaseModel, Field
from typing import Literal

# This model forces the AI to output exactly this JSON structure
class ExpenseDetailsExtraction(BaseModel):
    # Field(...) means it is strictly required. 
    # Descriptions help the LLM understand what to extract.
    amount: float = Field(..., description="Total Amount Spent. Numbers only.")
    category: Literal [
        "Food", "Travel", "Shopping", "Bills & Recharges", 
        "Money Transfers", "Entertainment", "Medical", 
        "Investment", "Donation", "Financial Services", 
        "Education", "Subscriptions", "Others"
    ] = Field(..., description="Expense Category (e.g., 'utilities', 'food', 'grocery').")
    item_description: str = Field(..., description="Short summary of what was bought.")


# This model validates the incoming data from WhatsApp chat
class WhatsAppMessage(BaseModel):
    sender_phone: str
    message_body: str