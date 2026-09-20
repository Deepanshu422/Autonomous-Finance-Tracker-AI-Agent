import re
from fastapi import APIRouter, HTTPException
from app.models.schemas import WhatsAppMessage
from app.services.db_crud import delete_latest_expense, get_weekly_summary, get_latest_pending_user, get_user_by_lid, get_user_by_phone, register_pending_user, update_user_role, delete_user, insert_expense
from app.services.llm_parser import extract_expense_data
from app.core.config import settings
from titlecase import titlecase


# Create a router specifically for webhook endpoints
router = APIRouter()

@router.post("/whatsapp")
async def handle_whatsapp_message(payload: WhatsAppMessage):
    whatsapp_lid = payload.sender_phone
    text = payload.message_body.strip()
    text_lower = text.lower()
    print("lid or num", whatsapp_lid)
    # getting info
    user = get_user_by_lid(whatsapp_lid)

    """REGISTRATION FLOW"""

    if not user:
        # Check if user replying with the correct format
        if "name:" in text_lower and ("whatsapp number:" in text_lower or "whatsapp:" in text_lower):
            try:
                name_part = re.search(r'name:\s*([a-zA-Z ]+)', text, re.IGNORECASE)
                phone_part = re.search(r'(?:whatsapp number|whatsapp):\s*(\+?\d+)', text, re.IGNORECASE)
                
                extracted_name = name_part.group(1).strip() if name_part else "Unknown"
                extracted_phone = phone_part.group(1).strip().replace(" ", "") if phone_part else ""

                if not extracted_phone:
                    return {"reply": "❌ Could not read the pshone number. Please ensure it has the country code (e.g., +91)."}

                # Save to database
                register_pending_user(whatsapp_lid, extracted_phone, extracted_name)

                # success message 
                return {
                    "reply": f"Thanks {extracted_name}! ⏳ Your request has been sent to the Admin for approval.",
                    "notify_admin": settings.admin_phone_number,
                    "notify_admin_message": f"🔔 New Bot Request!\nName: {extracted_name}\nWhatsApp Number: {extracted_phone}\n\nReply 'Y' to Approve\nReply 'N' to Reject\n(Or use #approve {extracted_phone})"
                }
            except Exception as e:
                return {"reply": "❌ Error parsing details. Please use the exact format provided:\n\nName: Your Name\nWhatsApp Number: +91XXXXXXXXXX"}
        
        # If they just said "Hi" or invalid format, send the onboarding template
        onboarding_msg = (
            "🤖 *Welcome to AI Money Tracker!*\n\n"
            "You are not registered yet. To request access, please reply exactly in this format:\n\n"
            "Name: Your Name\n"
            "WhatsApp Number: +91XXXXXXXXXX"
        )
        return {"reply": onboarding_msg}

    
    """PENDING APPROVAL CHECK"""

    if not user.get("is_approved"):
        return {"reply": f"⏳ Hi {user.get('name')}, your account is still pending for approval."}
    
    # Admin Commands Logic

    """ADMIN QUICK APPROVAL (Y/N)"""

    current_role = user.get("role")

    if current_role in ["super_admin", "admin"] and text_lower in ["y", "n"]:
        latest_pending = get_latest_pending_user()

        print("test", latest_pending)


        if not latest_pending:
            return {"reply": "✅ No pending requests found in the queue."}

        target_phone = latest_pending["phone_number"]
        target_name = latest_pending["name"]

        if text_lower == "y":
            update_user_role(target_phone, True, "user")
            return {
                "reply": f"✅ {target_name} ({target_phone}) has been approved as user!",
                "notify_user": target_phone,
                "notify_message": "🎉 Access granted! You can now start logging your expenses."
            }
        elif text_lower == "n":
            delete_user(target_phone)
            return {"reply": f"🚫 {target_name} ({target_phone}) has been rejected."}
        


    """HASHTAG (#) ADMIN COMMANDS"""

    if current_role in ["super_admin", "admin"] and text.startswith("#"):
        command_parts = text.split(" ")
        command = command_parts[0].lower()
        target_phone = command_parts[1] if len(command_parts) > 1 else ""

        if not target_phone:
            return {"reply": "❌ Please provide a phone number. Example: #approve +91XXXXXXXXXX"}

        target_user = get_user_by_phone(target_phone)
        if not target_user:
            return {"reply": f"❌ Could not find {target_phone} in the database."}

        target_role = target_user.get("role")

        # Role Based Access on commands
        if command == "#approve":
            updated = update_user_role(target_phone, True, "user")
            if updated:
                return {
                    "reply": f"✅ {target_phone} has been approved as a User!",
                    "notify_user": target_phone,
                    "notify_message": "🎉 Access granted! You can now start logging your expenses."
                }
            return {"reply": f"❌ Failed to approve {target_phone}."}

        elif command == "#reject":
            # Role security check
            if current_role == "admin" and target_role in ["super_admin", "admin"]:
                return {"reply": "❌ Permission denied: You cannot reject an Admin or Super Admin."}
            
            deleted = delete_user(target_phone)
            if deleted:
                return {
                    "reply": f"🚫 {target_phone} has been rejected and deleted.",
                    "notify_user": target_phone,
                    "notify_message": f"Your account has been rejected by admin!"
                }
            return {"reply": f"❌ Failed to reject {target_phone}."}

        elif command == "#makeadmin":
            # only forsuper_admin
            if current_role != "super_admin":
                return {"reply": "❌ Permission denied: Only a Super Admin can promote users to Admin."}
                
            updated = update_user_role(target_phone, True, "admin")
            if updated:
                return {
                    "reply": f"👑 {target_phone} has been promoted to Admin!",
                    "notify_user": target_phone,
                    "notify_message": "👑 You have been promoted to Admin! You can now use #approve and #reject commands."
                }
            return {"reply": f"❌ Failed to promote {target_phone}."}
            
        else:
             return {"reply": "❌ Unknown command. Available commands: #approve, #reject, #makeadmin"}

    """USER MAIN MENU COMMANDS"""
    if text == "2":
        summary_data = get_weekly_summary(user["id"])

        reply_msg = "📊 *Your Weekly Summary*\n\nYour spending in the last 7 days:\n"
        for category, amount in summary_data["categories"].items():
            reply_msg += f"{titlecase(category)} : ₹{amount}\n"

        reply_msg += f"\nYou spent a total of *₹{summary_data['total']}* in the last 7 days."
        return {"reply": reply_msg}
        
    elif text == "3":
        deleted_exp = delete_latest_expense(user["id"])
        if deleted_exp:
            return {"reply": f"🗑️ Deleted last expense: ₹{deleted_exp['amount']} for '{deleted_exp['category']}'."}
        return {"reply": "❌ No recent expenses found to delete."}

    
    """EXPENSE LOGGING"""

    try:
        parsed_data = extract_expense_data(text)
        print("test", parsed_data)
        if parsed_data:
            insert_expense(
                user_id=user["id"],
                amount=parsed_data["amount"],
                category=parsed_data["category"],
                description=parsed_data["item_description"]
            )

            # Attaching Action Menu
            menu_text = (
                "\n\n📊 *Main Menu:*\n"
                "Reply *2* for Weekly Summary\n"
                "Reply *3* to Delete Last Expense"
            )

            return {"reply": f"✅ Logged ₹{parsed_data['amount']} under '{parsed_data['category']}' ({parsed_data['item_description']})." + menu_text}
        else:
            return {"reply": "❌ I couldn't understand that expense. Please try again (e.g., 'spent 50 on chai')."}
    except Exception as e:
        print(f"Error parsing expense: {e}")
        return {"reply": "❌ An error occurred while processing your expense."}