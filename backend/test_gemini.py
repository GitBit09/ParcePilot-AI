import os
from dotenv import load_dotenv
load_dotenv('.env')
from openai import OpenAI
from agent.tools.tool_registry import TOOL_DEFINITIONS

client = OpenAI(
    api_key=os.getenv('GEMINI_API_KEY'),
    base_url='https://generativelanguage.googleapis.com/v1beta/openai/'
)

res = client.chat.completions.create(
    model='gemini-3.5-flash',
    messages=[{'role': 'user', 'content': 'Show me my orders'}],
    tools=TOOL_DEFINITIONS
)
print('Response:', res.choices[0].message)
