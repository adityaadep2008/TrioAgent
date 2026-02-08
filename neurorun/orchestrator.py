import os
import time
import asyncio
import json
import base64
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from PIL import Image

try:
    from droidrun.agent.droid import DroidAgent
    from droidrun.tools import AdbTools
    from droidrun.adb import DeviceManager
    from droidrun.agent.utils.llm_picker import load_llm
except ImportError:
    print("Critical: DroidRun SDK not found.")
    raise

class NeuroOrchestrator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not api_key:
            raise ValueError("API Key required for NeuroOrchestrator")
        
        # Configure Gemini for Vision/Planning
        genai.configure(api_key=self.api_key)
        self.planner_model = genai.GenerativeModel('gemini-2.0-flash-exp') # Use flash for speed, or pro for reasoning
        
        self.device_serial = None
        self.tools = None
        self.width = 1080 
        self.height = 2400
        self.step_limit = 15
        self.history: List[Dict] = []

    async def connect(self):
        """Connect to device and initialize tools"""
        try:
            dm = DeviceManager()
            devices = await dm.list_devices()
            if not devices:
                print("NeuroOrchestrator: No device found.")
                return False
            self.device_serial = devices[0].serial
            print(f"NeuroOrchestrator: Connected to {self.device_serial}")
            self.tools = AdbTools(serial=self.device_serial)
            
            # Get Resolution
            try:
                # Direct ADB call to get size
                stream = os.popen(f"adb -s {self.device_serial} shell wm size")
                out = stream.read().strip() # e.g., Physical size: 1080x2400
                if "size:" in out:
                    res = out.split("size:")[1].strip().split("x")
                    self.width = int(res[0])
                    self.height = int(res[1])
                    print(f"Detected Resolution: {self.width}x{self.height}")
                else:
                     self.width = 1080
                     self.height = 2400
            except:
                self.width = 1080
                self.height = 2400
            return True
        except Exception as e:
            print(f"NeuroOrchestrator Connection Error: {e}")
            return False

    async def capture_state_image(self) -> Optional[Image.Image]:
        try:
            path = f"neuro_state_{int(time.time())}.png"
            os.system(f"adb -s {self.device_serial} shell screencap -p /sdcard/neuro_cap.png")
            os.system(f"adb -s {self.device_serial} pull /sdcard/neuro_cap.png {path}")
            
            if os.path.exists(path):
                img = Image.open(path)
                return img
            return None
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return None

    def plan_next_step(self, main_goal: str, current_image: Image.Image, step_count: int) -> Dict:
        """
        Uses Vision to output exact COORDINATES or TEXT args.
        """
        prompt = f"""
        You are an advanced Android Automation Brain.
        Main Goal: {main_goal}
        Step: {step_count}/{self.step_limit}
        History: {[h['action'] for h in self.history]}

        Analyze the screenshot. The device resolution is implied 1000x1000 relative for coordinates.
        Identify the NEXT single action.
        - If the keyboard is open and blocking the view, use "back" to close it ONLY if you are NOT currently typing/searching.
        - If you are searching, DO NOT use "back" as it might exit the search. Instead, proceed to tap the result IF VISIBLE.
        - If the desired item (like 'Fries' image) is ALREADY visible, prefer 'tap' over 'type'.
        
        Output valid JSON only:
        {{
            "analysis": "Thinking process...",
            "status": "continue" | "done" | "failed",
            "action": {{
                "type": "tap" | "type" | "key" | "wait" | "back" | "home" | "done",
                "bq_box": [ymin, xmin, ymax, xmax] (0-1000 scale) - REQUIRED for 'tap', OPTIONAL for 'type' (to tap first),
                "text": "..." (REQUIRED for 'type'),
                "keycode": "..." (OPTIONAL for 'key'),
                "data": {{...}} (REQUIRED if status='done', extracted info)
            }}
        }}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add delay to respect rate limits
                if attempt > 0:
                    time.sleep(2) 
                
                response = self.planner_model.generate_content([prompt, current_image])
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                return json.loads(text)
            except Exception as e:
                print(f"Planning Error (Attempt {attempt+1}): {e}")
                if "429" in str(e) or "ResourceExhausted" in str(e) or "quota" in str(e).lower():
                    wait_time = (attempt + 1) * 5
                    print(f"Quota hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break
        
        return {"status": "failed", "analysis": "Failed after retries", "action": {"type": "wait"}}

    async def execute_action_direct(self, action: Dict):
        """
        Executes action directly via ADB.
        """
        tipo = action.get('type')
        print(f"  [Act] Executing: {tipo} | {action}")
        
        if tipo == 'tap':
            box = action.get('bq_box')
            if box:
                # box is [ymin, xmin, ymax, xmax] 0-1000
                ymin, xmin, ymax, xmax = box
                cx = (xmin + xmax) / 2 / 1000 * self.width
                cy = (ymin + ymax) / 2 / 1000 * self.height
                cmd = f"adb -s {self.device_serial} shell input tap {int(cx)} {int(cy)}"
                os.system(cmd)
                return "Tapped"
                
        elif tipo == 'type':
            text = action.get('text', '')
            
            # Standard input text is most compatible with standard keyboards
            # We escape spaces
            clean_text = text.replace(" ", "%s")
            os.system(f"adb -s {self.device_serial} shell input text {clean_text}")
            
            # Hit Enter to search
            time.sleep(1.5)
            os.system(f"adb -s {self.device_serial} shell input keyevent 66")
            return f"Typed {text}"
            
        elif tipo == 'key':
            code = action.get('keycode', '')
            os.system(f"adb -s {self.device_serial} shell input keyevent {code}")
            return f"Key {code}"
            
        elif tipo == 'back':
            os.system(f"adb -s {self.device_serial} shell input keyevent 4")
            return "Back (Close Keyboard/Nav)"
            
        elif tipo == 'home':
            os.system(f"adb -s {self.device_serial} shell input keyevent 3")
            return "Home"
            
        elif tipo == 'wait':
            time.sleep(2)
            return "Waited"
            
        return "Unknown Action"

    async def execute_subtask(self, instruction: str):
        """
        Spawns a DroidAgent for a single instruction (Atomic Execution) - Legacy/Fallback
        """
        print(f"  [Executor] Running: {instruction}")
        
        # Load LLM for the agent (Executor)
        llm = load_llm(
            provider_name="GoogleGenAI", 
            model="models/gemini-2.0-flash", 
            api_key=self.api_key
        )
        
        # We use a short max_steps because this is a sub-task
        agent = DroidAgent(
            goal=instruction,
            llm=llm,
            tools=self.tools,
            max_steps=5, # Atomic!
            debug=True,
            vision=False 
        )
        
        handler = agent.run()
        if hasattr(handler, "stream_events"):
            async for event in handler.stream_events():
                pass
        result = await handler
        return result

    async def run_mission(self, goal: str):
        print(f"NeuroOrchestrator Mission (Direct Mode): {goal}")
        if not await self.connect():
            return {"status": "failed", "error": "Connection Failed"}

        for i in range(1, self.step_limit + 1):
            print(f"\n--- Step {i}/{self.step_limit} ---")
            
            img = await self.capture_state_image()
            if not img:
                return {"status": "failed", "error": "Vision Lost"}
                
            plan = self.plan_next_step(goal, img, i)
            print(f"Brain: {plan.get('analysis', '...')}")
            
            action = plan.get('action', {})
            status = plan.get('status', 'continue')
            
            if status == 'done':
                print("Mission Success!")
                return {"status": "success", "data": action.get("data", {})}
            if status == 'failed':
                return {"status": "failed", "error": plan.get("analysis")}
            
            # Act Direct
            await self.execute_action_direct(action)
            
            self.history.append({"action": action})
            time.sleep(2) # Stabilize UI

        return {"status": "timeout", "error": "Limit reached"}
