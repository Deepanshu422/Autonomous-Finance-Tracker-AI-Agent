import httpx
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.db_crud import supabase, get_weekly_summary
from titlecase import titlecase


scheduler = AsyncIOScheduler()

async def send_weekly_summary():
    print(f"[{datetime.now()}] 🤖 Agent waking up to generate weekly summaries...")

    # Fetch all approved users
    users_response = supabase.table("users").select("id, phone_number").eq("is_approved", True).execute()
    users = users_response.data

    if not users:
        print("No approved users found.")
        return

    for user in users:
        user_id = user["id"]
        phone = user["phone_number"]

        # Use the category-wise function 
        summary_data = get_weekly_summary(user_id)

        # message layout
        if summary_data["total"] > 0:
            message = "📊 *Your Weekly Expense Summary*\n\nYour spending in the last 7 days:\n"
            for cat, amt in summary_data["categories"].items():
                message += f"• {titlecase(cat)} : ₹{amt}\n"
            message += f"\nYou spent a total of *₹{summary_data['total']}* in the last 7 days.\nKeep up the good tracking!"
        else:
            message = "📊 *Your Weekly Expense Summary*\n\nYou spent *₹0* in the last 7 days. Great job saving!"

        # Pushing to Express API
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://127.0.0.1:3000/api/send",
                    json={"phone_number": phone, "message": message},
                    timeout=15.0 # Increased timeout slightly for safety
                )
            print(f"✅ Summary sent to {phone}")
        except Exception as e:
            print(f"❌ Failed to push summary to {phone}: {e}")

def start_agent_scheduler():
    # Set to run daily at exactly 12:35 PM
    scheduler.add_job(send_weekly_summary, 'cron', hour=22, minute=00)
    scheduler.start()
    print("⏰ Autonomous Agent Scheduler started for 12:35 daily!")