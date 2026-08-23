import asyncio, json
import logging
logging.basicConfig(level=logging.DEBUG)

from agent.orchestrator import run_agent
from auth.mock_auth import AuthUser

async def main():
    print("Start main")
    user = AuthUser(user_id='northstar_user', account_id='ACCT-001', account_name='Northstar Logistics', role='customer', display_name='Northstar User')
    messages = [{'role': 'user', 'content': 'Show me all my recent orders'}]
    print("Calling run_agent")
    async for event in run_agent(messages, user):
        print("EVENT:", event)
    print("End main")

asyncio.run(main())
