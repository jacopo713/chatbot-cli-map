#!/usr/bin/env python3
"""
Debug what the AI is actually responding for categorization
"""
import sys
sys.path.append('.')

import asyncio
from main import call_model_once

async def debug_ai_categorization():
    """Test exactly what the AI responds for categorization"""
    
    test_message = "mi chiamo jacopo, ho 29 anni, mi piace la palestra, sono ansioso e ho il doc"
    
    extraction_prompt = f"""Analyze the following user message and extract ONLY relevant personal information in structured format with categories. The input message can be in any language.
Message: "{test_message}"

EXTRACT information using these EXACT formats (one per line):
- user_name: [person's name] | category:personal
- user_age: [age in numbers] | category:personal
- user_location: [city, country, region where they live] | category:personal
- user_job: [profession, work, occupation] | category:work
- user_likes: [what they like, hobbies, passions, interests - one per line] | category:hobby
- user_dislikes: [what they don't like, hate] | category:hobby
- user_condition: [medical conditions, psychological states, disorders] | category:health
- user_skill: [competencies, abilities, things they're good at] | category:work
- user_goal: [objectives, aspirations, future desires] | category:goals
- user_experience: [significant experiences, background] | category:personal
- user_relationship: [marital status, family relationships] | category:relationships
- user_preference: [specific preferences, personal choices] | category:personal

AVAILABLE CATEGORIES:
- personal: Basic personal info (name, age, location, preferences)
- work: Professional info (job, skills, work experience)
- hobby: Interests and recreational activities (likes, dislikes, hobbies)
- health: Medical and psychological conditions
- relationships: Family, romantic, social relationships
- goals: Future aspirations, objectives, plans

CRITICAL RULES:
1. Extract ONLY information explicitly mentioned in the message
2. DO NOT invent or deduce information that is not present
3. If there is NO personal information, respond: "NO_INFORMATION"
4. Use EXACTLY the format: type:value | category:category_name
5. For multiple elements of the same type, use separate lines
6. Always assign the most appropriate category from the list above
7. DO NOT add explanations, comments or extra text

EXAMPLES:
Input: "Mi chiamo Sara e ho 25 anni, vivo a Milano"
Output: 
user_name:Sara | category:personal
user_age:25 | category:personal
user_location:Milano | category:personal

Input: "I work as a software engineer and I love programming"
Output:
user_job:software engineer | category:work
user_likes:programming | category:hobby

Input: "Je suis anxieux et j'ai des TOC, j'aimerais devenir médecin"
Output:
user_condition:anxiety | category:health
user_condition:OCD | category:health
user_goal:become doctor | category:goals

Input: "What's the weather today?"
Output: NO_INFORMATION"""

    print("🔍 TEST: Debug AI categorization")
    print(f"📝 Input: {test_message}")
    print("=" * 60)
    
    try:
        response = await call_model_once([
            {"role": "user", "content": extraction_prompt}
        ], temperature=0.1)
        
        print("🤖 AI RESPONSE:")
        print(response)
        print("=" * 60)
        
        # Parse exactly like the real code
        facts = []
        if response and "NO_INFORMATION" not in response:
            lines = response.strip().split('\n')
            print(f"📋 PARSED LINES ({len(lines)}):")
            for i, line in enumerate(lines):
                line = line.strip()
                print(f"  {i+1}: '{line}'")
                
                if line and '|' in line:
                    try:
                        fact_part, category_part = line.split('|', 1)
                        fact_part = fact_part.strip()
                        category_part = category_part.strip()
                        
                        if fact_part and ':' in fact_part and category_part.startswith('category:'):
                            fact_type, fact_value = fact_part.split(':', 1)
                            category = category_part.replace('category:', '').strip()
                            
                            print(f"    ✅ type={fact_type}, value={fact_value}, category={category}")
                            facts.append(f"{fact_type}:{fact_value}|{category}")
                        else:
                            print(f"    ❌ Invalid format")
                    except Exception as e:
                        print(f"    ❌ Parse error: {e}")
        
        print(f"📊 FINAL FACTS ({len(facts)}):")
        for fact in facts:
            print(f"  • {fact}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_ai_categorization())