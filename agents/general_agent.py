import os
import json
import asyncio
import sys
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
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from agents.agent_factory import AgentFactory

load_dotenv()

class GeneralAgent:
    """
    The 'Brain' of the Agentic OS.
    - Maintains conversation history.
    - Classifies Intent: CHAT vs ACTION.
    - Asks clarifying questions if ACTION parameters are missing.
    - Delegates to Specialized Agents or AgentFactory.
    """
    
    def __init__(self, provider="gemini", model="models/gemini-2.5-flash"):
        self.provider = provider
        self.model = model
        # Simple in-memory session store: { session_id: [messages] }
        self.sessions: Dict[str, List[Dict]] = {}

        # Initialize specialized agents
        # We need to add root to path to import them
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
            
        try:
            from commerce_agent import CommerceAgent
            from ride_comparison_agent import RideComparisonAgent
            # Initialize them
            self.food_agent = CommerceAgent(model=model)
            self.ride_agent = RideComparisonAgent(model=model)
            print("✅ Specialized Agents Loaded in GeneralAgent")
        except ImportError as e:
            print(f"⚠️ Warning: Specialized agents could not be imported: {e}")
            self.food_agent = None
            self.ride_agent = None
        
        # System Prompt defines the persona and outputs
        self.system_prompt = (
            "You are 'Sanjeevani', a helpful, patience, and smart Agentic OS assistant designed for elders. "
            "Your goal is to help them navigate their phone and perform tasks. "
            "Tone: Warm, respectful, clear, and reassuring."
            "\n"
            "MEMORY RULES:\n"
            "1. ALWAYS remember previous turns in the conversation.\n"
            "2. If user provides details (like 'Fried Rice') in one turn and confirms app (like 'Zomato') in the next, COMBINE them.\n"
            "\n"
            "CAPABILITIES & JSON OUTPUTS:\n"
            "1. Order Food (Zomato/Swiggy)\n"
            "   Required: 'item' (e.g. 'Fried Rice'), 'action' ('order' or 'search')\n"
            "   Output: { \"type\": \"execute\", \"domain\": \"food\", \"item\": \"...\", \"action\": \"order/search\", \"app_preference\": \"Zomato/Swiggy/None\" }\n"
            "2. Book Rides (Uber/Ola)\n"
            "   Required: 'pickup', 'drop', 'type' (optional)\n"
            "   Output: { \"type\": \"execute\", \"domain\": \"ride\", \"pickup\": \"...\", \"drop\": \"...\", \"mode\": \"cab\" }\n"
            "3. General Tasks\n"
            "   Output: { \"type\": \"execute\", \"domain\": \"general\", \"app\": \"App Name\", \"instruction\": \"...\" }\n"
            "\n"
            "PROTOCOL:\n"
            "1. ANALYZE user input + History.\n"
            "2. IF user wants to chat/greet -> Reply warmly.\n"
            "3. IF user wants a task -> CHECK if all details are present.\n"
            "4. IF details missing -> ASK clarifying question.\n"
            "5. IF details clear -> RETURN the JSON block.\n"
            "\n"
            "OUTPUT FORMAT:\n"
            "If replying/asking: Just plain text.\n"
            "If ready to execute: Wrapp JSON in ```json ... ```"
        )

    async def chat(self, session_id: str, user_text: str) -> Dict[str, Any]:
        """
        Main entry point. Returns { "response": "...", "action_debug": ... }
        """
        # 1. Initialize Session if needed
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        history = self.sessions[session_id]
        
        # 2. Add User Message
        history.append({"role": "user", "parts": [user_text]})
        
        # 3. Call LLM
        response_text = await self._call_llm(history)
        
        # 4. Parse Response for Actions
        action = None
        clean_text = response_text
        
        try:
            import re
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group(1))
                if json_data.get("type") == "execute":
                    action = json_data
                    # If there's a 'speak' field, use it, otherwise use a generic message
                    clean_text = json_data.get("speak", "One moment, I am handling that for you.")
                    
                    # 5. EXECUTE AGENT
                    print(f"🤖 Triggering Domain: {action.get('domain')} - {action}")
                    
                    execution_result = await self._execute_action(action)
                    
                    # Enhance the response with the result
                    if execution_result.get("status") == "success":
                         msg = execution_result.get("message", "Task completed.")
                         clean_text = f"Done! {msg}"
                         # Add price details if implicit
                         if 'details' in execution_result and 'price' in str(execution_result['details']):
                             clean_text += " I found some good options."
                    else:
                         clean_text = f"I encountered an issue: {execution_result.get('error', 'Unknown Error')}"

        except Exception as e:
            print(f"Error parsing/executing agent response: {e}")
            clean_text += f" (System Error: {str(e)})"
        
        # 6. Update History with Assistant Response
        history.append({"role": "model", "parts": [response_text]})
        
        return {
            "response": clean_text,
            "action_debug": action
        }

    async def _execute_action(self, action: Dict) -> Dict:
        """Routes the action to the correct specialized agent."""
        domain = action.get("domain")
        
        try:
            # --- FOOD DOMAIN ---
            if domain == "food" and self.food_agent:
                item = action.get("item")
                act = action.get("action", "search")
                app_pref = action.get("app_preference")
                
                # Check specifics
                if act == "order" and not app_pref:
                    # Autonomous auto-order
                    return await self.food_agent.auto_order_cheapest(item)
                else:
                    # Specific app or search
                    target_app = app_pref if app_pref and app_pref != "None" else "Zomato"
                    return await self.food_agent.execute_task(target_app, item, "food item", action=act)

            # --- RIDE DOMAIN ---
            elif domain == "ride" and self.ride_agent:
                pickup = action.get("pickup")
                drop = action.get("drop")
                mode = action.get("mode", "cab")
                
                # Use book_cheapest_ride wrapper
                return await self.ride_agent.book_cheapest_ride(pickup, drop, mode)

            # --- GENERAL / FALLBACK ---
            else:
                # Default to AgentFactory (Autonomous DroidRun)
                app_name = action.get("app")
                instruction = action.get("instruction")
                if not instruction:
                    # Construct instruction from domain info if general agent failed to generate one
                    instruction = f"Open {app_name} and do the task."
                
                return await AgentFactory.run_task(
                    app_identifier=app_name, 
                    instruction=instruction,
                    provider=self.provider,
                    model=self.model
                )
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _call_llm(self, history: List[Dict]) -> str:
        """Helper to call Gemini via Google GenAI SDK"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key: return "Configuration Error: API Key missing."

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.model)
            
            # Construct Chat History
            # We insert the System Prompt into the very first turn to ensure persistence
            # Logic: If history is empty, start with System Prompt.
            # If history exists, we assume the first message already had it? 
            # No, 'history' arg is just the raw list.
            
            chat_history = []
            
            # Prepend System Prompt to the first user message if possible
            # or use system_instruction if supported (Gemini 1.5 supports it nicely)
            # Let's try system_instruction first, it's cleaner.
            
            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=self.system_prompt
            )
            
            # Convert roles
            for h in history:
                role = "user" if h["role"] == "user" else "model"
                parts = h["parts"]
                chat_history.append({"role": role, "parts": parts})
            
            # Start Chat
            # Use history[:-1] as past, and last msg as new input
            if chat_history:
                last_msg = chat_history[-1]
                past_history = chat_history[:-1]
                
                chat = model.start_chat(history=past_history)
                response = chat.send_message(last_msg["parts"][0])
                return response.text
            else:
                return "Hello! How can I help?"
                
        except Exception as e:
            print(f"LLM Error: {e}")
            return f"I am having trouble thinking right now. ({e})"
