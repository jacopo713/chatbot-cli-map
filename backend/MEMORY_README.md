# Sistema di Memoria - Chatbot CLI Map

## Panoramica

Il sistema di memoria implementa un recupero intelligente della memoria conversazionale utilizzando:

- **Cohere**: Per la generazione di embeddings semantici
- **Pinecone**: Per lo storage vettoriale e la ricerca semantica
- **Design scalabile**: Architettura modulare per future espansioni

## Funzionalità

### ✅ Implementate
- **Storage automatico**: Ogni conversazione viene automaticamente memorizzata
- **Ricerca semantica**: Recupero di memorie rilevanti basato su similarità semantica
- **Contesto conversazionale**: Recupero automatico del contesto per nuovi messaggi
- **Isolamento per conversazione**: Le memorie possono essere filtrate per conversazione
- **Metadata ricchi**: Storage di metadati aggiuntivi (progetto, mappe concettuali, ecc.)
- **API endpoints**: `/api/memory/status` e `/api/memory/search`
- **Indicatore frontend**: Stato della memoria visibile nell'interfaccia

### 🚀 Funzionalità scalabili future
- **Cleanup automatico**: Rimozione di memorie vecchie
- **Categorizzazione**: Classificazione automatica delle memorie
- **Personalizzazione**: Memorie specifiche per utente
- **Analytics**: Statistiche sull'utilizzo della memoria
- **Backup/Restore**: Esportazione e importazione delle memorie

## Configurazione

### Variabili d'ambiente richieste:
```bash
COHERE_API_KEY=your_cohere_key_here
PINECONE_API_KEY=your_pinecone_key_here  
PINECONE_INDEX=chatbot-cli-map
PINECONE_HOST=your_pinecone_host_here
```

### Dipendenze Python:
```
cohere>=5.0.0
pinecone-client>=5.0.0
pydantic>=2.0.0
```

## Architettura

### Componenti principali:

1. **MemoryService** (`memory_service.py`)
   - Gestione centralized di storage e retrieval
   - Integrazione con Cohere per embeddings
   - Integrazione con Pinecone per vector search

2. **Integration con FastAPI** (`main.py`)
   - Auto-storage delle conversazioni
   - Recupero automatico del contesto
   - Endpoints per gestione memoria

3. **Frontend Integration** (`api.ts`, `Chatbot.tsx`)
   - Indicatori di stato memoria
   - API per ricerca memoria (futuro)

### Flusso dati:

```
User Message → Generate Embedding → Store in Pinecone
     ↓
Query Context → Semantic Search → Retrieve Relevant Memories
     ↓
Context + Current Message → LLM → Response
     ↓
Store Response → Generate Embedding → Update Memory
```

## Testing

Usa il file `test_memory.py` per testare il sistema:

```bash
cd backend
python test_memory.py
```

Questo script testa:
- Connessione ai servizi
- Storage delle memorie
- Retrieval semantico
- Contesto conversazionale

## Performance

### Configurazione attuale:
- **Modello embedding**: `embed-multilingual-v3.0` (Cohere)
- **Dimensioni vettore**: 1024
- **Soglia similarità**: 0.7
- **Limit default**: 5 memorie per query

### Ottimizzazioni implementate:
- **Async operations**: Tutte le operazioni sono asincrone
- **Batch processing**: Storage asincrono delle conversazioni
- **Context pruning**: Limitazione automatica del contesto
- **Error handling**: Graceful degradation se memoria non disponibile

## Monitoring

Il sistema logga:
- Inizializzazione servizi
- Storage/retrieval operations
- Errori e warning
- Statistiche utilizzo

## Security

- **API keys** separate per Cohere e Pinecone
- **Conversation isolation** tramite metadata
- **Sanitization** degli input
- **Rate limiting** (da implementare se necessario)

## Estensioni future

### 🔄 In pianificazione:
- **User-specific memories**: Memorie per utenti specifici
- **Memory tagging**: Sistema di tag per classificazione
- **Memory importance scoring**: Pesi di importanza automatici
- **Cross-conversation learning**: Apprendimento tra conversazioni
- **Memory compression**: Summarization di conversazioni lunghe
- **Real-time memory updates**: Aggiornamenti in tempo reale