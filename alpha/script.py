from openai import OpenAI
import os, re
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

load_dotenv(find_dotenv(usecwd=True), override=True)

raw = os.getenv("OPENAI_API_KEY")
api_key = (raw or "").strip().strip('"').strip("'") 
if not api_key.startswith(("sk-", "sk-proj-")) or len(api_key) < 40:
    raise ValueError("OPENAI_API_KEY looks wrong.")

client = OpenAI()
def get_script():
    chat = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "An overworked, underappreciated adult child or partner, writing in a confessional, vindicated tone, trying to prove they were right to strangers online while venting about betrayal, manipulation, or entitlement."},
            {"role": "user", "content": "Generate a strictly 2000 word reddit styled story (with rich punctuation for text to speech models to pick up on) from the person venting's point of view story following the prompt: I have just realized that my former friend was in love with my ex-husband the whole time. "},
        ],
    )
    print(chat.choices[0].message.content)
    from openai import OpenAI
    client = OpenAI()
    return 
