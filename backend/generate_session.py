import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_ID or not API_HASH:
    print("Please set API_ID and API_HASH in your .env file first.")
    exit(1)

async def main():
    async with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
        print("Session String (Save this as SESSION_STRING in .env):")
        print(await app.export_session_string())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
