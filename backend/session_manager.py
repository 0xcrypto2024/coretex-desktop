import os
import sys
import logging
import asyncio
from pyrogram import Client, errors
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def update_env_session(new_session):
    """Updates the SESSION_STRING in the .env file."""
    env_path = ".env"
    if not os.path.exists(env_path):
        logger.error(".env file not found!")
        return

    try:
        with open(env_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        session_updated = False
        
        for line in lines:
            if line.startswith("SESSION_STRING="):
                new_lines.append(f"SESSION_STRING={new_session}\n")
                session_updated = True
            else:
                new_lines.append(line)
        
        if not session_updated:
            new_lines.append(f"\nSESSION_STRING={new_session}\n")
            
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        logger.info("✅ .env updated with new SESSION_STRING")
    except Exception as e:
        logger.error(f"Failed to update .env: {e}")

async def interactive_renewal(api_id, api_hash):
    """Performs interactive login to generate a new session string."""
    print("\n" + "="*50)
    print("🔓 STARTING INTERACTIVE LOGIN")
    print("="*50)
    print("Please check your Telegram app for the Login Code.")
    
    # Use memory storage for generation to avoid locking files
    async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        session_string = await app.export_session_string()
        return session_string

async def ensure_session(api_id, api_hash, session_string):
    """
    Validates the session. If invalid or missing, triggers interactive renewal.
    Returns the valid session string (new or existing).
    """
    
    # 1. Check if empty
    if not session_string or len(session_string.strip()) == 0:
        logger.warning("⚠️ SESSION_STRING is empty. Starting interactive login...")
        new_session = await interactive_renewal(api_id, api_hash)
        return new_session, True # True = updated

    # 2. Check if valid (Attempt Connect)
    async def validate():
        try:
            # InMemory to avoid database locks during check
            client = Client(":memory:", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True)
            await client.start()
            me = await client.get_me()
            await client.stop()
            return True
        except (errors.AuthKeyUnregistered, errors.UserDeactivated, errors.SessionRevoked, errors.AuthKeyInvalid):
            return False
        except Exception as e:
            # If it's a network error or unrelated, we might not want to force re-login immediately,
            # but for "Not Acceptable" (406) or 401s, we definitely do.
            logger.error(f"Session validation error: {e}")
            # Assume invalid if we can't start
            return False

    is_valid = await validate()
    
    if not is_valid:
        logger.warning("⚠️ Session is INVALID or REVOKED. Renewal required.")
        new_session = await interactive_renewal(api_id, api_hash)
        return new_session, True
        
    return session_string, False
