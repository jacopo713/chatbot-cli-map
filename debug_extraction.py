#!/usr/bin/env python3
"""
Debug dell'estrazione per capire dove si blocca
"""
import sys
sys.path.append('.')

import asyncio
import logging
from hybrid_memory_service import HybridMemoryService, HybridMemoryConfig

# Setup logging per debug
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("debug_extraction")

async def debug_extraction_flow():
    """Debug completo del flusso di estrazione"""
    
    logger.info("🔍 INIZIO DEBUG ESTRAZIONE")
    
    config = HybridMemoryConfig(
        cohere_api_key="dummy",
        pinecone_api_key="dummy"
    )
    service = HybridMemoryService(config)
    
    test_message = "mi chiamo jacopo, vivo a brovello carpugnino, mi piacciono i cani e i gatti"
    
    # Test step by step
    logger.info(f"📝 Test messaggio: '{test_message}'")
    
    try:
        # Step 1: Controllo se è considerato info personale
        logger.info("🔍 Step 1: Controllo _contains_personal_info...")
        is_personal = service._contains_personal_info(test_message)
        logger.info(f"✅ Is personal info: {is_personal}")
        
        # Step 2: Test estrazione diretta
        logger.info("🔍 Step 2: Test estrazione diretta...")
        facts = await service._extract_canonical_facts(test_message)
        logger.info(f"✅ Fatti estratti: {len(facts)}")
        
        if facts:
            for i, fact in enumerate(facts, 1):
                logger.info(f"   {i}. {fact}")
        else:
            logger.warning("⚠️  Nessun fatto estratto!")
            
        # Step 3: Test risposta IA raw
        logger.info("🔍 Step 3: Test risposta IA raw...")
        from main import call_model_once
        
        extraction_prompt = f"""Analizza: "{test_message}"

ESTRAI informazioni in formato: tipo:valore

ESEMPI:
- "Mi chiamo Sara" → user_name:Sara
- "Vivo a Milano" → user_location:Milano  
- "Mi piacciono i cani" → user_likes:cani

Se non ci sono info, rispondi: NESSUNA_INFORMAZIONE"""

        response = await call_model_once([
            {"role": "user", "content": extraction_prompt}
        ], temperature=0.1)
        
        logger.info(f"🤖 Risposta IA RAW: '{response}'")
        logger.info(f"📊 Lunghezza risposta: {len(response)} caratteri")
        
        # Step 4: Test parsing della risposta
        logger.info("🔍 Step 4: Test parsing risposta...")
        
        lines = response.strip().split('\n')
        logger.info(f"📄 Righe trovate: {len(lines)}")
        
        for i, line in enumerate(lines, 1):
            logger.info(f"   Riga {i}: '{line.strip()}'")
            line = line.strip()
            if ':' in line:
                if line.count(':') == 1:
                    fact_type, fact_value = line.split(':', 1)
                    logger.info(f"      → Parsed: tipo='{fact_type.strip()}', valore='{fact_value.strip()}'")
                else:
                    logger.warning(f"      ⚠️  Troppi ':' in riga: {line}")
            else:
                logger.info(f"      ℹ️  Nessun ':' in riga: {line}")
        
    except Exception as e:
        logger.error(f"❌ ERRORE: {e}", exc_info=True)
    
    logger.info("✅ DEBUG COMPLETATO")

if __name__ == "__main__":
    asyncio.run(debug_extraction_flow())