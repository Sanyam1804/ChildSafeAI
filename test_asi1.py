
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("ASI1_API_KEY")

if not api_key:
    raise RuntimeError("ASI1_API_KEY not found in .env")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.asi1.ai/v1",
)

try:
    response = client.chat.completions.create(
        model="asi1",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: ChildSafe AI connection successful"
            }
        ],
    )

    print("API connection successful!")
    print(response.choices[0].message.content)

except Exception as error:
    print("API request failed.")
    print(type(error).__name__, str(error))
