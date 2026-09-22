from pydantic import BaseModel, Field
from typing import Literal, List

# This model forces the AI to output exactly this JSON structure
class ExpenseDetailsExtraction(BaseModel):
    # Field(...) means it is strictly required. 
    # Descriptions help the LLM understand what to extract.
    amount: float = Field(..., description="Total Amount Spent. Numbers only.")
    category: Literal [
        "Food", "Travel", "Shopping", "Bills & Recharges", "Stationary",
        "Money Transfers", "Entertainment", "Medical", "Grocery", "Sports"
        "Investment", "Donation", "Financial Services", 
        "Education", "Subscriptions", "Others"
    ] = Field(..., description="Expense Category (e.g., 'Sports', 'Food', 'Grocery').")
    item_description: str = Field(..., description="Short summary of what was bought.")

class ExpenseExtraction(BaseModel):
    expenses: List[ExpenseDetailsExtraction] = Field(..., description="A list of all expenses extracted from the user's message.")

# This model validates the incoming data from WhatsApp chat
class WhatsAppMessage(BaseModel):
    sender_phone: str
    message_body: str