#!/usr/bin/env python3

import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def _load_env_fallback():
    try:
        p = Path("backend/.env")
        if p.exists():
            for raw in p.read_text(encoding="utf-8").splitlines():
                s = raw.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip(); v = v.strip()
                if k and (k not in os.environ):
                    os.environ[k] = v
    except Exception:
        pass

_load_env_fallback()

from zai import ZaiClient

async def test_glm_direct():
    """Test diretto di GLM 4.5 per capire il problema"""
    
    # Initialize ZAI client
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("❌ ZAI_API_KEY not found")
        return
    
    try:
        client = ZaiClient(api_key=api_key)
    except TypeError:
        # Fallback for different ZAI client versions
        api_url = os.getenv("ZAI_API_URL", "https://api.z.ai/api/paas/v4")
        client = ZaiClient(api_key=api_key, api_url=api_url)
    
    print("🧪 Test diretto GLM 4.5")
    print("="*50)
    
    # Test prompts
    test_prompts = [
        "Ciao, dimmi solo: ciao",
        "Rispondi con un semplice JSON: {\"test\": \"ok\"}",
        """Scomponi questa domanda: "Quale sistema mi consigli per la memoria?"
        
Rispondi SOLO con JSON:
{
  "sub_queries": [
    {
      "id": "sq1", 
      "question": "esempio domanda",
      "priority": 1,
      "estimated_complexity": "bassa"
    }
  ]
}""",
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- TEST {i} ---")
        print(f"Prompt: {prompt[:50]}...")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            def sync_call():
                return client.chat.completions.create(
                    model="glm-4.5",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, sync_call)
            
            if response and response.choices:
                content = response.choices[0].message.content
                print(f"✅ Response: '{content}'")
                print(f"   Length: {len(content) if content else 0}")
                print(f"   Type: {type(content)}")
            else:
                print("❌ No response/choices")
                print(f"   Response object: {response}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_glm_direct())