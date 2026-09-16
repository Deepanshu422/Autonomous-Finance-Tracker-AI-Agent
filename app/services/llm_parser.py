import json
from groq import Groq
from app.core.config import settings
from app.models.schemas import ExpenseDetailsExtraction

# Intializing 'Groq' client
client = Groq(api_key=settings.groq_api_key)

def extract_expense_data(user_text: str) -> dict | None:
    # Converting Pydantic Model into string
    schema_definition = ExpenseDetailsExtraction.model_json_schema()

    system_prompt = f"""
    Extract the expense details from the user's text.
    Output strictly in JSON format matching this schema: {json.dumps(schema_definition)}        
    """

    try:
        # Connecting with llm
        chat_completion = client.chat.completions.create(
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
        validated_data = ExpenseDetailsExtraction(**parsed_data)

        return validated_data.model_dump()

    except Exception as e:
        print(f"Extraction failed : {e}")
        return None
    

        


