import httpx
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.db_crud import supabase, get_summary

scheduler = AsyncIOScheduler()

async def send_daily_summary():
    print(f"[{datetime.now()}] 🤖 Agent waking up to generate daily summaries...")
    # Get the current time in HH:MM:00 format
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time_str = now.strftime("%H:%M:00")
    try:
        # Fetching approved users
        users_response = supabase.table("users").select("id, phone_number").eq("is_approved", True).eq("daily_summary_active", True).eq("daily_summary_time", current_time_str).execute()
        users = users_response.data
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    if not users:
        print("No approved users found.")
        return

    print(f"[{now}] 🤖 Found {len(users)} users scheduled for {current_time_str}. Sending...")

    async with httpx.AsyncClient() as client:
        for user in users:
            user_id = user["id"]
            phone = user["phone_number"]

            try:
                # Fetching yesterday's summary (last 24 hours)
                summary_data = get_summary(user_id, days=1)

                # Format the message
                if summary_data["total"] > 0:
                    message = "📊 *Your Daily Expense Summary*\n\nYour spending in the last 24 hours:\n"

                    for cat, amt in summary_data["categories"].items():
                        message += f"• {cat.title()} : ₹{amt}\n"

                    message += f"\nTotal spent: *₹{summary_data['total']}*"

                else:
                    message = "📊 *Your Daily Expense Summary*\n\nYou spent *₹0* in the last 24 hours. Great job saving!"

                # Pushing to Node.js Gateway
                await client.post(
                    "http://127.0.0.1:3000/send",
                    json={"phone_number": phone, "message": message},
                    timeout=10.0
                )
                print(f"✅ Summary sent to {phone}")
                
                # Rate Limiting: To prevent bot get banned from Meta
                await asyncio.sleep(0.5) 
                
            except Exception as e:
                # Fault Isolation: Log failure, but loop will continue
                print(f"❌ Failed to process summary for {phone}: {e}")

def start_agent_scheduler():
    # Schedule for exactly 10:00 PM IST daily
    scheduler.add_job(
        send_daily_summary, 
        'cron', 
        minute='*', 
        timezone=ZoneInfo("Asia/Kolkata")
    )
    scheduler.start()
    print("⏰ Autonomous Agent Scheduler started for 10:00 PM IST daily!")