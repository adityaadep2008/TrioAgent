import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import DroidRun LLM tools for the Brain
try:
    from droidrun.agent.utils.llm_picker import load_llm
except ImportError:
    pass # Will handle gracefully if missing

# Import Agent Factory
try:
    from agents.agent_factory import AgentFactory
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from agents.agent_factory import AgentFactory

load_dotenv()

class GeneralAgent:
    """
    The 'Brain' of the Agentic OS.
    - Maintains conversation history.
    - Classifies Intent: CHAT vs ACTION.
    - Asks clarifying questions if ACTION parameters are missing.
    - Delegates to AgentFactory.
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        # Simple in-memory session store: { session_id: [messages] }
        # In prod, use Redis/DB.
        self.sessions: Dict[str, List[Dict]] = {}
        
        # System Prompt defines the persona
        self.system_prompt = (
            "You are 'Sanjeevani', a helpful, patience, and smart Agentic OS assistant designed for elders. "
            "Your goal is to help them navigate their phone and perform tasks. "
            "Tone: Warm, respectful, clear, and reassuring. "
            "\n"
            "CAPABILITIES:\n"
            "1. Book Rides (Uber, Ola)\n"
            "2. Order Food (Zomato, Swiggy)\n"
            "3. Buy Medicine (PharmEasy, Apollo)\n"
            "4. Book Flights/Hotels (MakeMyTrip, Booking.com)\n"
            "5. Send Messages (WhatsApp)\n"
            "\n"
            "PROTOCOL:\n"
            "1. ANALYZE user input.\n"
            "2. IF user wants to chat/greet -> Reply warmly.\n"
            "3. IF user wants a task -> CHECK if all details are present.\n"
            "   - Cab: pickup, drop, type (optional)\n"
            "   - Food: item, app (optional)\n"
            "   - Medicine: name\n"
            "   - Message: contact, message\n"
            "4. IF details missing -> ASK clarifying question (one at a time).\n"
            "5. IF details clear -> RETURN a special JSON block to trigger action.\n"
            "\n"
            "OUTPUT FORMAT:\n"
            "If replying/asking: Just plain text.\n"
            "If ready to execute: \n"
            "```json\n"
            "{\n"
            "  \"type\": \"execute\",\n"
            "  \"app\": \"App Name\",\n"
            "  \"instruction\": \"Exact step-by-step goal for the agent...\",\n"
            "  \"speak\": \"Okay, I am booking that for you now.\"\n"
            "}\n"
            "```"
        )

    async def chat(self, session_id: str, user_text: str) -> Dict[str, Any]:
        """
        Main entry point. Returns { "text": "...", "action": ... }
        """
        # 1. Initialize Session
        if session_id not in self.sessions:
            self.sessions[session_id] = [
                {"role": "user", "parts": [f"System: {self.system_prompt}"]} # Priming
            ]
        
        history = self.sessions[session_id]
        history.append({"role": "user", "parts": [user_text]})
        
        # 2. Call LLM (Using DroidRun's LLM Picker or direct)
        response_text = await self._call_llm(history)
        
        # 3. Parse Response
        action = None
        clean_text = response_text
        
        try:
            import re
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(1))
                if json_data.get("type") == "execute":
                    action = json_data
                    clean_text = json_data.get("speak", "Executing task...")
                    
                    # 4. EXECUTE AGENT IF ACTION DETECTED
                    print(f"🤖 Triggering Agent: {action['app']}")
                    
                    # Run in background or await? 
                    # For responsiveness, we usually await if it's fast, or return "Started"
                    # User asked for "Not Fail", so let's await to confirm start, 
                    # but maybe the actual long-running task should be async.
                    # For this demo, we'll await the result to give immediate feedback.
                    
                    agent_res = await AgentFactory.run_task(
                        app_identifier=action['app'],
                        instruction=action['instruction'],
                        provider=self.provider,
                        model=self.model
                    )
                    
                    if agent_res.get("status") == "success":
                         clean_text = f"Done! {agent_res.get('message', 'Task completed successfully.')}"
                         # Add specific details if available
                         if 'price' in str(agent_res): 
                             clean_text += f" The price is {agent_res.get('price', '')}."
                    else:
                         clean_text = f"I tried, but ran into an issue: {agent_res.get('error', 'Unknown error')}."
            
        except Exception as e:
            print(f"Error parsing general agent response: {e}")
        
        # 5. Update History
        history.append({"role": "model", "parts": [response_text]})
        
        return {
            "response": clean_text,
            "action_debug": action
        }

    async def _call_llm(self, history: List[Dict]) -> str:
        """Helper to call Gemini via DroidRun or Direct"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # Simplify history for API consumption if needed, 
        # but Gemini SDK handles the list format well usually.
        # We'll use a direct generation here for simplicity/speed if DroidRun is heavy,
        # but let's try to align with the project's imports if possible.
        
        try:
            import google.generativeai as genai
            if not api_key: return "Configuration Error: API Key missing."
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)
            
            # Convert history to Gemini format (User/Model)
            chat_history = []
            for h in history:
                role = "user" if h["role"] == "user" else "model"
                # Handle system prompt hack (Gemini doesn't support 'system' role in chat usually, 
                # so we merged it into first user message or use system_instruction in beta)
                parts = h["parts"]
                chat_history.append({"role": role, "parts": parts})
            
            # Generate
            # We treat the whole thing as a chat session or just send valid history
            # To be safe, let's just use generate_content with the list
            # But the first item is our 'System' hack. The library might complain if we feed it directly execution.
            
            # Quick hack: Consolidate strict history for the chat object
            # Ideally we keep a persistent chat object, but for REST API statelessness we rebuild.
            
            chat = model.start_chat(history=chat_history[:-1]) # All except last
            response = chat.send_message(chat_history[-1]["parts"][0])
            return response.text
            
        except Exception as e:
            return f"I'm sorry, my brain is having trouble connecting. Error: {e}"
