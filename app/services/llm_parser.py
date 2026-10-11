import json
from groq import AsyncGroq
from app.core.config import settings
from app.models.schemas import ExpenseExtraction, UpdateAlertTime, RouteToExpense
from app.services.db_crud import update_summary_time
import base64
import tempfile
import os

# Intializing 'Groq' client
client = AsyncGroq(api_key=settings.groq_api_key)

async def transcribe_voice_note(audio_base64: str) -> str:
    """Decodes base64 audio and transcribes it using Groq Whisper."""
    audio_bytes = base64.b64decode(audio_base64)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_file_path = tmp_file.name

    try:
        with open(tmp_file_path, "rb") as file:
            transcription = await client.audio.transcriptions.create(
                file=(tmp_file_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="text"
            )
        return transcription
    except Exception as e:
        print(f"❌ Whisper Transcription failed: {e}")
        return None
    finally:
        # Prevent memory leaks by deleting the temp file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

async def extract_expense_data(user_text: str) -> dict | None:
    # Converting Pydantic Model into string
    schema_definition = ExpenseExtraction.model_json_schema()

    system_prompt = f"""
    Extract the expense details from the user's text.
    Output strictly in JSON format matching this schema: {json.dumps(schema_definition)}        
    """

    try:
        # Connecting with llm
        chat_completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="openai/gpt-oss-120b",
            # response_format={"type":"json"},
            temperature=0.0 # For zero creativity, but maximum precision
        )

        # Extract str response and parse it as dict
        raw_json = chat_completion.choices[0].message.content
        parsed_data = json.loads(raw_json)

        # verifying using our Pydantic Model
        print("Parsed Data :", parsed_data)

        validated_data = ExpenseExtraction.model_validate(parsed_data)

        return validated_data.model_dump()

    except Exception as e:
        print(f"Extraction failed : {e}")
        return None
    
async def process_with_groq(user_text: str, user_id: str) -> str:
    """
    Dedicated function for Option 6. 
    Uses native Tool Calling with Pydantic to parse time accurately.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "update_alert_time",
                "parameters": UpdateAlertTime.model_json_schema()
            }
        }
    ]

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "Extract the time and convert to 24-hour HH:MM:SS format."},
                {"role": "user", "content": user_text}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "update_alert_time"}}, # Force the tool
            temperature=0.0
        )

        tool_calls = response.choices[0].message.tool_calls

        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            time_str = args.get("time_str")
            # Execute database update
            return update_summary_time(user_id, time_str)

        return "❌ Could not detect a valid time."

    except Exception as e:
        print(f"Time extraction failed: {e}")
        return "❌ System error while updating time."