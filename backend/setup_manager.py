from pyrogram import Client
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SetupManager:
    def __init__(self):
        self.temp_client: Optional[Client] = None
        self.phone_number: Optional[str] = None
        self.phone_code_hash: Optional[str] = None
        self.is_authorized = False

    async def connect(self, api_id: int, api_hash: str):
        self.temp_client = Client(":memory:", api_id=api_id, api_hash=api_hash)
        await self.temp_client.connect()
        logger.info("Setup Client Connected")

    async def send_code(self, phone: str):
        if not self.temp_client:
            raise ValueError("Client not connected.")
        self.phone_number = phone
        sent = await self.temp_client.send_code(phone)
        self.phone_code_hash = sent.phone_code_hash
        return {"status": "code_sent", "type": str(sent.type)}

    async def verify_code(self, code: str):
        if not self.temp_client or not self.phone_number or not self.phone_code_hash:
            raise ValueError("Flow interrupted.")
        try:
            await self.temp_client.sign_in(self.phone_number, self.phone_code_hash, code)
            self.is_authorized = True
            return await self._finalize_login()
        except Exception as e:
            if "SESSION_PASSWORD_NEEDED" in str(e):
                return {"status": "password_needed"}
            raise e

    async def verify_password(self, password: str):
        if not self.temp_client: raise ValueError("Client lost.")
        await self.temp_client.check_password(password)
        self.is_authorized = True
        return await self._finalize_login()

    async def _finalize_login(self):
        string = await self.temp_client.export_session_string()
        await self.temp_client.disconnect()
        self.temp_client = None
        return {"status": "success", "session_string": string}
