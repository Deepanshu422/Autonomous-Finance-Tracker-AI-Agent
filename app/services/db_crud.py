from datetime import datetime, timedelta
from supabase import create_client, Client
from app.core.config import settings

# Initializing supabase Client using secure settings
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

def get_latest_pending_user() -> dict | None:
    # fetching most recent regiestered user
    response = supabase.table("users").select("*").eq("is_approved", False).order("created_at", desc=True).limit(1).execute()
    return response.data[0] if response.data else None

def get_weekly_summary(user_id: str) -> float:
    # Calculates the total spent by a user in the last 7 days.
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    response = supabase.table("expenses").select("amount", "category").eq("user_id", user_id).gte("created_at", seven_days_ago).execute()

    summary_data = {"categories": {}, "total": 0.0}
    if response.data:
        for item in response.data:
            category = item["category"]
            amount = item["amount"]
            summary_data["categories"][category] = summary_data["categories"].get(category, 0.0) + amount
            summary_data["total"] += amount

    return summary_data


def delete_latest_expense(user_id: str) -> dict | None:
    # Finds and deletes the most recent expense for a user.
    # Order by created_at descending and limit to 1 to get the latest
    response = supabase.table("expenses").select("id, amount, category").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    
    if not response.data:
        return None
        
    expense_id = response.data[0]["id"]
    supabase.table("expenses").delete().eq("id", expense_id).execute()
    return response.data[0]

def get_user_by_lid(whatsapp_lid: str) -> dict | None:
    # check user using LID
    response = supabase.table("users").select("*").eq("whatsapp_lid", whatsapp_lid).execute()
    return response.data[0] if response.data else None

def get_user_by_phone(phone_number: str) -> dict | None:
    # Get user by phone number to check their role before admin actions
    response = supabase.table("users").select("*").eq("phone_number", phone_number).execute()
    return response.data[0] if response.data else None


def register_pending_user(whatsapp_lid: str, real_phone_number: str, name: str) -> dict | None:
    # Save user with pending status, for avoiding multiple spam requests
    data = {
        "whatsapp_lid": whatsapp_lid,
        "phone_number": real_phone_number,
        "name": name,
        "is_approved": False,
        "role": "user"
    }
    response = supabase.table("users").upsert(data).execute()
    return response.data[0] if response.data else None

def update_user_role(target_phone: str, is_approved: bool, role: str) -> dict | None:
    # Update using the real phone number
    data = {
        "is_approved": is_approved, 
        "role": role
    }
    response = supabase.table("users").update(data).eq("phone_number", target_phone).execute()
    return response.data[0] if response.data else None


def delete_user(target_phone: str):
    # Completely remove the unwanted user 
    response = supabase.table("users").delete().eq("phone_number", target_phone).execute()
    return response.data[0] if response.data else None
    
def insert_expense(user_id: str, amount: float, category: str, description: str = "") -> dict | None:
    # Saves expense using the UUID Foreign Key.
    data = {
        "user_id": user_id,  # Linked to users.id
        "amount": amount,
        "category": category,
        "description": description
    }
    response = supabase.table("expenses").insert(data).execute()
    return response.data[0] if response.data else None