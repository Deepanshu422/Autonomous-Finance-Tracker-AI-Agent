from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from app.core.config import settings

# Initializing supabase Client using secure settings
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

def get_latest_pending_user() -> dict | None:
    # fetching most recent regiestered user
    response = supabase.table("users").select("*").eq("is_approved", False).order("created_at", desc=True).limit(1).execute()
    return response.data[0] if response.data else None

def toggle_summary_alerts(user_id: str) -> str:
    user_response = supabase.table("users").select("daily_summary_active").eq("id", user_id).execute()
    if not user_response.data:
        return "❌ User profile not found."

    new_state = not user_response.data[0].get("daily_summary_active", True)
    supabase.table("users").update({"daily_summary_active": new_state}).eq("id", user_id).execute()
    
    status_text = "resumed 🟢" if new_state else "paused ⏸️"
    return f"✅ Your daily summaries are now {status_text}." 

def update_summary_time(user_id: str, new_time: str) -> str:
    try:
        supabase.table("users").update({"daily_summary_time": new_time}).eq("id", user_id).execute()
        return f"⏰ Daily summary time successfully changed to {new_time}."
    except Exception:
        return "❌ Failed to update time. Please try again."

def format_summary_message(timeframe: str, summary_data: dict) -> str:
    
    # Takes summary dict and formats it in whatsApp-friendly message.
    
    if summary_data["total"] > 0:
        message = f"📊 *{timeframe} Expense Summary*\n\n"
        for cat, amt in summary_data["categories"].items():
            message += f"• {cat.title()} : ₹{amt}\n"
        message += f"\nTotal spent: *₹{summary_data['total']}*"
        return message
    else:
        return f"📊 *{timeframe} Expense Summary*\n\nYou spent *₹0*. Great job saving!"

def get_summary(user_id: str, days: int) -> dict:
    
    # Calculating user's total spending dynamically based on the 'days' parameter.

    # Supabase databases are set to UTC by default
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    response = supabase.table("expenses") \
        .select("amount", "category") \
        .eq("user_id", user_id) \
        .gte("created_at", start_date) \
        .execute()

    summary_data = {"categories": {}, "total": 0.0}
    
    if response.data:
        for item in response.data:
            category = item.get("category", "Uncategorized")
            amount = float(item.get("amount", 0.0))
            
            # Aggregate categories dynamically
            summary_data["categories"][category] = summary_data["categories"].get(category, 0.0) + amount
            summary_data["total"] += amount

    summary_data["total"] = round(summary_data["total"], 2)
    for cat in summary_data["categories"]:
        summary_data["categories"][cat] = round(summary_data["categories"][cat], 2)

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
    
def insert_expense(user_id: str, expenses_list: list[dict]) -> list[dict] | None:
    # 1. Format the data into a list of dictionaries mapping to your database columns
    batch_data = [
        {
            "user_id": user_id,
            "amount": exp["amount"],
            "category": exp["category"],
            "description": exp.get("item_description", "")
        }
        for exp in expenses_list
    ]
    
    # inserting into db
    response = supabase.table("expenses").insert(batch_data).execute()
    
    return response.data if response.data else None