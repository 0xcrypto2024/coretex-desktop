from google import genai
from google.genai import types
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from config import GENAI_KEY, GENAI_MODEL

class Agent:
    def __init__(self):
        self.api_key = GENAI_KEY
        if not self.api_key:
            logger.warning("GENAI_KEY not found. Agent will not function correctly.")
            self.model_name = None
            return
        
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = GENAI_MODEL
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.client = None

    async def analyze_message(self, message_text: str, sender_info: str, user_name: str, memory_text: str = "") -> dict:
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
                prompt = template.render(memory_text=memory_text, message_text=message_text, user_name=user_name)
        except Exception as e:
            logger.error(f"Failed to load system_prompt.txt: {e}")
            # Fallback (Generic)
            prompt = f"Analyze this chat: {message_text}. Memory: {memory_text}. Json output."
        
        import asyncio
        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
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
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Failed to generate summary."
    async def analyze_context_batch(self, history_text: str, user_name: str) -> list:
        """
        Analyzes a batch of chat history to extract persistent user facts.
        Returns a list of strings (facts).
        """
        if not history_text: return []
        
        prompt = f"""
        Read the following Telegram chat history.
        Identify and extract any PERSISTENT facts, identities, roles, or preferences about the user ("Me" or "{user_name}").
        
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
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            return data.get("facts", [])
        except Exception as e:
            logger.error(f"Error analyzing context batch: {e}")
            return []

    async def analyze_feedback_batch(self, feedback_text: str) -> list:
        """
        Analyzes a batch of rejected tasks and comments to extract permanent rules.
        """
        if not feedback_text: return []
        
        prompt = f"""
        Analyze the following REJECTED tasks and the user's comments explaining why.
        Extract PERMANENT rules or preferences that I (the Agent) should follow to avoid these mistakes in the future.
        
        Focus on:
        - Scheduling constraints (e.g. "No meetings on Friday")
        - Content filters (e.g. "Ignore crypto news")
        - Priority adjustments (e.g. "Newsletters are always P4")
        
        Ignore:
        - One-off mistakes that don't imply a general rule.
        
        Feedback History:
        {feedback_text}
        
        Output JSON ONLY:
        {{
            "rules": ["rule 1", "rule 2"]
        }}
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            return data.get("rules", [])
        except Exception as e:
            logger.error(f"Error analyzing feedback batch: {e}")
            return []

    async def deduplicate_facts(self, facts: list) -> list:
        """
        Consolidates a list of facts by removing duplicates and merging related items.
        """
        if not facts: return []
        
        # Optimization: Don't call AI for small lists
        if len(facts) < 5:
            return sorted(list(set(facts)))
        
        facts_text = json.dumps(facts, indent=2)
        
        prompt = f"""
        You are a memory optimizer.
        Review the following list of facts/memories about the user.
        
        Goal: CONSOLIDATE and DEDUPLICATE.
        
        Rules:
        1.  Merge identical or highly similar facts (e.g. "Works at TechCorp" + "TechCorp employee" -> "Works at TechCorp").
        2.  Resolve conflicts by keeping the most specific version (e.g. "Working on a project" vs "Working on Project X" -> "Working on Project X").
        3.  Group related concepts into single concise sentences if possible.
        4.  Maintain ALL unique information. Do not lose details.
        5.  Return a clean JSON list of strings.
        
        Input Facts:
        {facts_text}
        
        Output JSON ONLY:
        {{
            "consolidated_facts": [ ... ]
        }}
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            return data.get("consolidated_facts", [])
        except Exception as e:
            logger.error(f"Error deduplicating facts: {e}")
            return facts # Fail safe: return original list

    async def handle_session_turn(self, history_text: str, user_profile: str, user_name: str) -> dict:
        """
        Acts as a polite receptionist for interactive sessions.
        """
        prompt = f"""
        You are Cortex, an AI assistant acting as a receptionist for {user_name}.
        {user_name} is currently offline/unavailable.
        
        GOAL:
        Interact with the user to gather necessary details about their request so {user_name} can handle it efficiently later.
        
        CONTEXT:
        User Profile (What {user_name} does):
        {user_profile}
        
        Conversation So Far:
        {history_text}
        
        INSTRUCTIONS:
        1. Be polite, professional, and concise.
        2. If the user asks a question you can answer based on Profile, answer it.
        3. If the user wants to schedule something, ask for time/date.
        4. If the user reporting an issue, ask for details.
        5. DO NOT promise specific actions ("{user_name} will do this"). Say "I will let {user_name} know".
        6. If you have enough info, or the user says "thanks/bye", set status to FINISH.
        
        OUTPUT JSON ONLY:
        {{
            "reply": "Your message to the user...", 
            "status": "CONTINUE" or "FINISH"
        }}
        """
        
        try:
            logger.info(f"DEBUG: Calling Gemini for Session Turn. User: {user_name}, Prompt Length: {len(prompt)}")
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            logger.info(f"DEBUG: Gemini Raw Response: {response.text}")
            data = json.loads(response.text)
            return data
        except Exception as e:
            text_resp = getattr(response, 'text', 'None') if 'response' in locals() else 'None'
            logger.error(f"Error in session turn (Raw Response: {text_resp}): {e}")
            return {"reply": "I've noted that down. (Error)", "status": "FINISH"}

    async def summarize_session(self, history_text: str, user_name: str) -> dict:
        """
        Summarizes a finished interactive session into a Task.
        """
        prompt = f"""
        Analyze this finished conversation between a User and Cortex (AI Receptionist).
        
        Conversation:
        {history_text}
        
        Create a concise TASK for {user_name} based on the outcome.
        
        OUTPUT JSON ONLY:
        {{
            "summary": "Actionable task summary...",
            "priority": 1-4 (Int),
            "deadline": "YYYY-MM-DD" or null
        }}
        """
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            logger.error(f"Error summarizing session: {e}")
            return {"summary": "Review conversation (Summary Failed)", "priority": 3}
