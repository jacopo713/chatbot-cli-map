#!/usr/bin/env python3
"""
Test del sistema di estrazione con categorizzazione
"""
import sys
sys.path.append('.')

import asyncio
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

async def test_categorized_extraction():
    """Test estrazione con categorie"""
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    print("🏷️  Test estrazione CON CATEGORIZZAZIONE")
    print("="*50)
    
    test_cases = [
        # Mix di informazioni per testare diverse categorie
        "mi chiamo jacopo, ho 29 anni, lavoro come sviluppatore, mi piacciono i cani e sono ansioso",
        
        # Solo hobby
        "mi piace suonare la chitarra e ascoltare jazz",
        
        # Solo lavoro  
        "sono bravo in python e javascript, lavoro in una startup",
        
        # Solo salute
        "soffro di ansia e ho problemi di sonno",
        
        # Solo goals
        "vorrei diventare un esperto di AI e aprire la mia azienda"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: \"{message[:40]}...\"")
        
        try:
            facts = await service._extract_canonical_facts(message)
            
            if facts:
                print(f"   ✅ Extracted {len(facts)} categorized facts:")
                
                # Group by category
                by_category = {}
                for fact in facts:
                    if '|' in fact:
                        fact_content, category = fact.split('|', 1)
                        category = category.strip()
                    else:
                        fact_content = fact
                        category = 'general'
                    
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(fact_content)
                
                # Display by category
                category_emojis = {
                    'personal': '👤',
                    'work': '💼', 
                    'hobby': '🎨',
                    'health': '🏥',
                    'relationships': '👥',
                    'goals': '🎯',
                    'general': '📋'
                }
                
                for category, items in by_category.items():
                    emoji = category_emojis.get(category, '📋')
                    print(f"      {emoji} {category.upper()}:")
                    for item in items:
                        fact_type = item.split(':')[0] if ':' in item else 'info'
                        fact_value = item.split(':', 1)[1] if ':' in item else item
                        print(f"         • {fact_type}: {fact_value}")
                        
            else:
                print(f"   ⚪ No information extracted")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "="*50)
    print("✅ Test categorizzazione completato!")

if __name__ == "__main__":
    asyncio.run(test_categorized_extraction())