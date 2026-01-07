import google.generativeai as genai
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from config import GENAI_KEY

class Agent:
    def __init__(self):
        self.api_key = GENAI_KEY
        if not self.api_key:
            logger.warning("GENAI_KEY not found. Agent will not function correctly.")
            self.model = None
            return
        
        genai.configure(api_key=self.api_key)
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None

    async def analyze_message(self, message_text: str, sender_info: str, memory_text: str = "") -> dict:
        """
        Analyzes a message to determine importance and generate a summary.
        Returns a dictionary: { "priority": int, "summary": str, "action_required": bool, "deadline": str, "reply_text": str, "save_memory": str }
        """
        if not self.api_key:
            return {"priority": 0, "summary": "No API Key", "action_required": False}

        # Load Prompt from File for easy management
        try:
            from jinja2 import Template
            import sys
            # Fix for PyInstaller path
            if hasattr(sys, '_MEIPASS'):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(os.path.abspath("."))
                
            prompt_file = base_path / "system_prompt.txt"
            with open(prompt_file, "r") as f:
                template_str = f.read()
                template = Template(template_str)
                prompt = template.render(memory_text=memory_text, message_text=message_text)
        except Exception as e:
            logger.error(f"Failed to load system_prompt.txt: {e}")
            # Fallback (Generic)
            prompt = f"Analyze this chat: {message_text}. Memory: {memory_text}. Json output."
        
        import asyncio
        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            try:
                response = await self.model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
                data = json.loads(response.text)
                
                # Robustness: Handle if AI returns a list instead of a dict
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                
                if not isinstance(data, dict):
                    logger.error(f"AI returned invalid format: {type(data)}")
                    return {"priority": 4, "summary": "Invalid analysis format", "action_required": False}
                    
                return data
            except Exception as e:
                # Handle Quota / Rate Limit (429)
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = backoff ** (attempt + 1)
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                    
                logger.error(f"Error analyzing message: {e}")
                return {"priority": 4, "summary": f"Analysis failed: {str(e)[:50]}", "action_required": False}
        
        return {"priority": 4, "summary": "Analysis failed after retries", "action_required": False}

    async def summarize_discussions(self, buffer_text: str) -> str:
        """
        Summarizes a list of discussion points into a cohesive daily report.
        """
        if not buffer_text: return "No meaningful discussions to report."
        
        prompt = f"""
        You are a helpful assistant summarizing the day's group chats.
        Here are the raw discussion points, grouped by chat:
        
        {buffer_text}
        
        Please provide a concise, bullet-point summary of the discussions.
        - Group by Chat Name.
        - Identify key topics and general sentiment.
        - Ignore trivial chatter.
        - Format neatly in Markdown.
        - Start with "📢 **Daily Group Discussion Digest**"
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Failed to generate summary."
    async def analyze_context_batch(self, history_text: str) -> list:
        """
        Analyzes a batch of chat history to extract persistent user facts.
        Returns a list of strings (facts).
        """
        if not history_text: return []
        
        prompt = f"""
        Read the following Telegram chat history.
        Identify and extract any PERSISTENT facts, identities, roles, or preferences about the user ("Me" or "JZ").
        
        Focus on:
        - Work Context (What projects are they working on?)
        - Technical Stack (What tools/languages do they use?)
        - Role (What is their job?)
        - Strong Preferences (e.g. "I hate calls")

        Ignore:
        - One-off tasks ("Buy milk")
        - Temporary states ("I'm tired")

        History:
        {history_text}

        Output JSON ONLY:
        {{
            "facts": ["fact 1", "fact 2"]
        }}
        """

        try:
            response = await self.model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            return data.get("facts", [])
        except Exception as e:
            logger.error(f"Error analyzing context batch: {e}")
            return []
