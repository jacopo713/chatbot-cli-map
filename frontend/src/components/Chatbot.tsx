"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';
import ErrorConsole from './ErrorConsole';
import ConceptMapPreview, { ConceptMapData } from './ConceptMapPreview';
import MemoryDashboard from './MemoryDashboard';
import { getMemoryStatus } from '@/lib/api';
import { useAuth } from '@/lib/AuthContext';
import { useFirebaseConceptMaps } from '@/lib/useFirebaseConceptMaps';

interface Message { text: string; sender: 'user' | 'ai'; reasoning?: string; }
interface Project { id: string; name: string; files: Array<{ path: string; content: string; language: string }>; autoCapture?: boolean; }
type FileEntry = { path: string; content: string; language: string };
type TreeNode = { name: string; path: string; type: 'dir' | 'file'; children?: TreeNode[]; file?: FileEntry; };
type ViewMode = 'chat' | 'map';
interface ConceptMapItem { id: string; name: string; data: ConceptMapData; updatedAt: number; }
interface Conversation { id: string; title: string; createdAt: number; updatedAt: number; messages: Message[]; }

function makeConversationId() {
  try { // @ts-ignore
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch {}
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}
function deriveTitleFrom(text: string, max = 48) {
  const t = text.replace(/\s+/g, ' ').trim();
  if (!t) return 'Nuova chat'; return t.length > max ? t.slice(0, max) + '…' : t;
}

export default function Chatbot() {
  const { user, logout } = useAuth();
  const { conceptMaps: firebaseMaps, saveConceptMap, updateConceptMap, deleteConceptMap, fetchConceptMaps } = useFirebaseConceptMaps();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [conversationId, setConversationId] = useState<string>(makeConversationId());
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [selectedMapId, setSelectedMapId] = useState<string | null>(null);
  const [renamingMapId, setRenamingMapId] = useState<string | null>(null);
  const [showCopyFeedback, setShowCopyFeedback] = useState<{ [key: number]: boolean }>({});
  const [showSaveFeedback, setShowSaveFeedback] = useState<{ [key: number]: boolean }>({});
  const [savedMessages, setSavedMessages] = useState<{ [key: number]: boolean }>({});
  const [savingMessages, setSavingMessages] = useState<{ [key: number]: boolean }>({});
  const [hiddenMapIds, setHiddenMapIds] = useState<Set<string>>(new Set());
  const [openedMapIds, setOpenedMapIds] = useState<Set<string>>(new Set());

  const [isFileModalOpen, setIsFileModalOpen] = useState(false);
  const [currentFile, setCurrentFile] = useState<{ path: string; content: string; language: string } | null>(null);
  const [isErrorConsoleOpen, setIsErrorConsoleOpen] = useState(false);
  const [recentlySavedFiles, setRecentlySavedFiles] = useState<Set<string>>(new Set());
  // Memory service status
  const [memoryAvailable, setMemoryAvailable] = useState<boolean>(false);
  const [memoryChecked, setMemoryChecked] = useState<boolean>(false);
  
  // Simplified frontend - no multi-agent system
  
  // Settings menu state
  const [showSettingsMenu, setShowSettingsMenu] = useState<boolean>(false);
  const [showMemoryDashboard, setShowMemoryDashboard] = useState<boolean>(false);


  // ───── Boot
  useEffect(() => {
    try { const p = localStorage.getItem('chatbot-projects'); if (p) setProjects(JSON.parse(p)); } catch {}
    // Maps are now stored in Firebase only
    try {
      const c = localStorage.getItem('***HIDDEN_KEY***');
      const active = localStorage.getItem('chatbot-active-conv');
      if (c) {
        const arr: Conversation[] = JSON.parse(c);
        setConversations(arr);
       
        const useId = (active && arr.find(x=>x.id===active)) ? active : (arr[0]?.id || conversationId);
        setConversationId(useId);
        const conv = arr.find(x=>x.id===useId);
        setMessages(conv?.messages || []);
      } else {
        setConversations([]); setMessages([]);
        setSavedMessages({}); setSavingMessages({}); setShowCopyFeedback({}); setShowSaveFeedback({});
        localStorage.removeItem('***HIDDEN_KEY***'); localStorage.removeItem('chatbot-active-conv');
      }
    } catch {}
    
    // Simplified frontend - no multi-agent preferences
    
    // Check memory service status
    const checkMemory = async () => {
      try {
        const status = await getMemoryStatus();
        setMemoryAvailable(status.available || false);
      } catch {
        setMemoryAvailable(false);
      } finally {
        setMemoryChecked(true);
      }
    };
    checkMemory();
    
    // Simplified frontend with direct GLM 4.5 calls
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(()=>{ localStorage.setItem('chatbot-projects', JSON.stringify(projects)); }, [projects]);
  // Maps are stored in Firebase, no localStorage needed
  useEffect(()=>{ localStorage.setItem('***HIDDEN_KEY***', JSON.stringify(conversations)); }, [conversations]); // Correzione qui
  // No multi-agent mode to persist
  
  // Close settings menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (showSettingsMenu && !target.closest('.settings-menu-container')) {
        setShowSettingsMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSettingsMenu]);
  useEffect(()=>{
    const exists = conversations.some(c=>c.id===conversationId);
    if (exists) localStorage.setItem('chatbot-active-conv', conversationId);
    else localStorage.removeItem('chatbot-active-conv');
  }, [conversationId, conversations]);

  useEffect(() => {
    const hasUserMsg = messages.some(m => m.sender === 'user'); if (!hasUserMsg) return;
    setConversations(prev => {
      const idx = prev.findIndex(c => c.id === conversationId);
      const firstUser = messages.find(m => m.sender === 'user');
      const currentTitle = idx >= 0 ? prev[idx].title : 'Nuova chat';
      const autoTitle = (currentTitle === 'Nuova chat' && firstUser) ? deriveTitleFrom(firstUser.text) : currentTitle;
      const updated: Conversation = idx >= 0 ? { ...prev[idx], title: autoTitle, messages, updatedAt: Date.now() } : {
        id: conversationId, title: autoTitle || 'Nuova chat', createdAt: Date.now(), updatedAt: Date.now(), messages
      };
      const next = idx >= 0 ? [...prev] : [...prev, updated]; if (idx >= 0) next[idx] = updated; next.sort((a,b)=>b.updatedAt-a.updatedAt); return next;
    });
  }, [messages, conversationId]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      if (messagesEndRef.current && chatContainerRef.current) {
        const el = chatContainerRef.current;
        const isAtBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 50;
        if (isAtBottom || messages.length === 0) messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  }, [messages.length]);

  useEffect(()=>{ if (!loading) scrollToBottom(); }, [messages, loading, scrollToBottom]);

  const showToast = useCallback((text: string, type: 'success' | 'info' | 'error' = 'info') => {
    const t = document.createElement('div');
    t.className = `fixed bottom-20 right-6 px-4 py-2 rounded-lg shadow-lg z-50 ${type==='success'?'bg-green-500':(type==='error'?'bg-red-500':'bg-blue-500')} text-white`;
    t.textContent = text; document.body.appendChild(t);
    setTimeout(()=>{ t.style.opacity='0'; t.style.transition='opacity .3s'; setTimeout(()=>document.body.removeChild(t),300); }, 2500);
  }, []);

  // Projects helpers
  const createNewProject = useCallback(() => {
    if (!newProjectName.trim()) return;
    const np: Project = { id: Date.now().toString(), name: newProjectName, files: [], autoCapture: false };
    setProjects(prev => [...prev, np]); setSelectedProjectId(np.id); setNewProjectName('');
  }, [newProjectName]);

  const toggleAutoCapture = useCallback((projectId: string) => {
    setProjects(prev => prev.map(p => p.id===projectId ? {...p, autoCapture: !p.autoCapture} : p));
  }, []);

  const addFileToProject = useCallback((filePath: string, content: string, language: string) => {
    if (!selectedProjectId) return;
    setProjects(prev => prev.map(project => {
      if (project.id !== selectedProjectId) return project;
      const i = project.files.findIndex(f => f.path === filePath);
      if (i>=0){ const files=[...project.files]; files[i]={path:filePath,content,language}; return {...project, files}; }
      return {...project, files:[...project.files,{path:filePath,content,language}]};
    }));
    setRecentlySavedFiles(prev=>new Set(prev).add(filePath));
    setTimeout(()=>setRecentlySavedFiles(prev=>{const s=new Set(prev); s.delete(filePath); return s;}), 2000);
    showToast(`💾 File salvato: ${filePath}`,'success');
  }, [selectedProjectId, showToast]);

  const removeFileFromProject = useCallback((filePath: string) => {
    if (!selectedProjectId) return;
    setProjects(prev => prev.map(p => p.id===selectedProjectId ? {...p, files: p.files.filter(f=>f.path!==filePath)} : p));
    setRecentlySavedFiles(prev=>{const s=new Set(prev); s.delete(filePath); return s;});
    showToast(`🗑️ File rimosso: ${filePath}`,'info');
  }, [selectedProjectId, showToast]);

  const buildFileTree = useCallback((files: FileEntry[]): TreeNode => {
    const root: TreeNode = { name:'', path:'', type:'dir', children:[] };
    const ensureDir = (parts: string[], base: TreeNode) => {
      let cur=base; for(const part of parts){ if(!part) continue; if(!cur.children) cur.children=[]; let next=cur.children.find(ch=>ch.type==='dir'&&ch.name===part);
        if(!next){ const full=(cur.path?cur.path+'/':'')+part; next={name:part,path:full,type:'dir',children:[]}; cur.children.push(next); } cur=next; }
      return cur;
    };
    for (const f of files) {
      const parts=f.path.split('/'); const fileName=parts.pop() as string; const dir=ensureDir(parts, root);
      if(!dir.children) dir.children=[]; const idx=dir.children.findIndex(ch=>ch.type==='file'&&ch.name===fileName);
      const node: TreeNode={name:fileName,path:(dir.path?dir.path+'/':'')+fileName,type:'file',file:f}; if(idx>=0) dir.children[idx]=node; else dir.children.push(node);
    }
    const sortTree=(n:TreeNode)=>{ if(!n.children) return; n.children.sort((a,b)=>a.type!==b.type?(a.type==='dir'?-1:1):a.name.localeCompare(b.name)); n.children.forEach(sortTree); };
    sortTree(root); return root;
  }, []);

  const openFile = useCallback((file: { path:string; content:string; language:string }) => { setCurrentFile(file); setIsFileModalOpen(true); }, []);

  const renderTree = useCallback((node: TreeNode, level=0): React.JSX.Element | null => {
    if (node.type==='file' && node.file){
      const isRecent = recentlySavedFiles.has(node.path);
      return (
        <div key={node.path} className={`text-xs text-gray-600 p-1 rounded hover:bg-gray-100 cursor-pointer flex items-center justify-between transition-all ${isRecent?'bg-green-50 border-l-2 border-green-500':''}`}>
          <div className="flex items-center flex-1" onClick={()=>openFile(node.file!)}>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1 text-gray-500" viewBox="0 0 24 24" fill="currentColor"><path d="M4 4h5l2 2h9v12a2 2 0 0 1-2 2H4z" /></svg>
            <span className="flex-1" style={{paddingLeft: level*8}}>{node.name}</span>
          </div>
          <button onClick={(e)=>{e.stopPropagation(); removeFileFromProject(node.path);}} className="ml-2 text-red-500 hover:text-red-700 p-1 rounded" title="Rimuovi file">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M9 3h6a1 1 0 0 1 1 1v1h4v2H4V5h4V4a1 1 0 0 1 1-1zm1 6h2v9h-2V9zm4 0h2v9h-2V9z" /></svg>
          </button>
        </div>
      );
    }
    if (node.type==='dir' && node.children && node.children.length>0){
      const isRoot=node.path==='';
      return (
        <div key={node.path||'root'} className={isRoot?'':'ml-2'}>
          {!isRoot && (
            <div className="text-[11px] font-semibold text-gray-700 flex items-center py-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1 text-amber-600" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4h4l2 2h4a2 2 0 0 1 2 2v2H2V8a2 2 0 0 1 2-2h4l2-2z" /></svg>
              {node.name}
            </div>
          )}
          <div className="ml-2">{node.children.map(ch=>renderTree(ch, isRoot?0:level+1))}</div>
        </div>
      );
    }
    return null;
  }, [recentlySavedFiles, openFile, removeFileFromProject]);

  const handleCodeBlockInteraction = useCallback((filePath: string, content: string, language: string, isAutoCapture=false) => {
    const p = projects.find(x=>x.id===selectedProjectId);
    if (selectedProjectId && (p?.autoCapture || !isAutoCapture)) addFileToProject(filePath, content, language);
    else if (!selectedProjectId && !isAutoCapture){ navigator.clipboard.writeText(content); showToast('📋 Copiato negli appunti','info'); }
  }, [selectedProjectId, projects, addFileToProject, showToast]);

  // Helper function to create a new concept map
  const createNewConceptMap = useCallback(async () => {
    const centerX = 900, centerY = 500;
    const mapName = 'Nuova mappa concettuale';
    const nodes = [
      {id:'root',label:'Obiettivo',x:centerX,y:centerY},
      {id:'req',label:'Requisiti',x:centerX-350,y:centerY-180},
      {id:'fe',label:'Front-end',x:centerX+350,y:centerY-180},
      {id:'be',label:'Back-end',x:centerX+350,y:centerY+180},
      {id:'ux',label:'UX/UI',x:centerX-350,y:centerY+180},
      {id:'test',label:'Test & QA',x:centerX,y:centerY+300}
    ];
    const edges = [
      {id:'e1',from:'root',to:'req'},
      {id:'e2',from:'root',to:'fe'},
      {id:'e3',from:'root',to:'be'},
      {id:'e4',from:'root',to:'ux'},
      {id:'e5',from:'root',to:'test'}
    ];
    
    const conceptMapData = { title: mapName, nodes, edges };
    const newMapId = await saveConceptMap(conceptMapData);
    
    if (newMapId) {
      setSelectedMapId(newMapId);
      setViewMode('map');
      // Add the new map to "opened" maps in sidebar
      setOpenedMapIds(prev => new Set([...prev, newMapId]));
      showToast('🗺️ Nuova mappa concettuale creata','success');
    } else {
      showToast('❌ Errore nella creazione della mappa','error');
    }
  }, [saveConceptMap, showToast, setSelectedMapId, setViewMode]);

  const closeFileModal = useCallback(()=>{ setIsFileModalOpen(false); setCurrentFile(null); }, []);

  // Convert Firebase maps to local format
  const convertedFirebaseMaps = useMemo(() => {
    return firebaseMaps.map(fbMap => ({
      id: fbMap.id || '',
      name: fbMap.title || 'Mappa senza titolo',
      data: {
        title: fbMap.title || 'Mappa senza titolo',
        nodes: fbMap.nodes || [],
        edges: fbMap.edges || []
      },
      updatedAt: fbMap.updatedAt ? new Date(fbMap.updatedAt).getTime() : Date.now()
    }));
  }, [firebaseMaps]);

  // Helper function to handle map changes (Firebase only)
  const handleMapChange = useCallback(async (mapId: string, newData: ConceptMapData) => {
    if (!mapId) return;
    // All maps are now Firebase maps, just update
    await updateConceptMap(mapId, newData);
  }, [updateConceptMap]);

  // Use only Firebase maps
  const selectedProject = projects.find(p=>p.id===selectedProjectId) || null;
  const selectedMap = convertedFirebaseMaps.find(m=>m.id===selectedMapId) || null;
  
  // Sidebar shows only "opened" Firebase maps
  const visibleMapsInSidebar = convertedFirebaseMaps.filter(m => 
    openedMapIds.has(m.id) && !hiddenMapIds.has(m.id)
  );
  
  // Main view shows all Firebase maps
  const allVisibleMaps = convertedFirebaseMaps.filter(m => !hiddenMapIds.has(m.id));

  const components = useMemo<Components>(() => ({
    code: ({ node, inline, className, children, ...props }: any) => (
      <CodeBlock
        node={node} inline={inline} className={className}
        onInteraction={handleCodeBlockInteraction}
        isAutoCaptureEnabled={projects.find(p=>p.id===selectedProjectId)?.autoCapture || false}
        hasActiveProject={!!selectedProjectId}
        projectFiles={selectedProject?.files || []}
        {...props}
      >
        {children}
      </CodeBlock>
    ),
    h1: ({ children, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-4 text-gray-800 border-b border-gray-200 pb-2" {...props}>{children}</h1>,
    h2: ({ children, ...props }) => <h2 className="text-xl font-bold mt-5 mb-3 text-gray-800 border-b border-gray-200 pb-2" {...props}>{children}</h2>,
    h3: ({ children, ...props }) => <h3 className="text-lg font-bold mt-4 mb-2 text-gray-800" {...props}>{children}</h3>,
    h4: ({ children, ...props }) => <h4 className="text-base font-bold mt-3 mb-2 text-gray-800" {...props}>{children}</h4>,
    p: ({ children, ...props }) => <p className="my-3 leading-relaxed text-gray-700" {...props}>{children}</p>,
    ul: ({ children, ...props }) => <ul className="list-disc pl-5 my-3 space-y-1" {...props}>{children}</ul>,
    ol: ({ children, ...props }) => <ol className="list-decimal pl-5 my-3 space-y-1" {...props}>{children}</ol>,
    li: ({ children, ...props }) => <li className="my-1 pl-2" {...props}>{children}</li>,
    blockquote: ({ children, ...props }) => (
      <blockquote className="border-l-4 border-blue-500 bg-blue-50 text-gray-800 p-4 my-4 rounded-r-lg" {...props}>{children}</blockquote>
    ),
    table: ({ children, ...props }) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse border border-gray-200 rounded-lg" {...props}>{children}</table>
      </div>
    ),
    thead: ({ children, ...props }) => <thead className="bg-gray-100" {...props}>{children}</thead>,
    tbody: ({ children, ...props }) => <tbody className="divide-y divide-gray-200" {...props}>{children}</tbody>,
    tr: ({ children, ...props }) => <tr className="hover:bg-gray-50" {...props}>{children}</tr>,
    th: ({ children, ...props }) => (
      <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b border-gray-300" {...props}>{children}</th>
    ),
    td: ({ children, ...props }) => (
      <td className="px-4 py-2 text-sm text-gray-700 border-b border-gray-200" {...props}>{children}</td>
    ),
    strong: ({ children, ...props }) => <strong className="font-semibold text-gray-900" {...props}>{children}</strong>,
    a: ({ href, ...props }) => <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer" {...props}/>,
  }), [handleCodeBlockInteraction, selectedProjectId, projects, selectedProject]);

  const buildMapContextText = useCallback((): string | null => {
    if (!selectedMap) return null;
    const adj = new Map<string,string[]>(); selectedMap.data.nodes.forEach(n=>adj.set(n.id,[]));
    selectedMap.data.edges.forEach(e=>{ const arr=adj.get(e.from); if (arr) arr.push(e.to); });
    let rootId = selectedMap.data.nodes[0]?.id ?? ''; let max=-1;
    for (const [k,v] of adj.entries()){ if (v.length>max){ max=v.length; rootId=k; } }
    const id2 = new Map(selectedMap.data.nodes.map(n=>[n.id,n.label]));
    const lines:string[]=[]; const vis=new Set<string>();
    function dfs(id:string, depth:number){ if (vis.has(id)) return; vis.add(id);
      lines.push(`${'  '.repeat(depth)}- ${id2.get(id) ?? id}`); (adj.get(id)||[]).forEach(c=>dfs(c, depth+1)); }
    if (rootId) dfs(rootId,0);
    return (selectedMap.data.title?`# ${selectedMap.data.title}\n\n`:'') + lines.join('\n');
  }, [selectedMap]);

  // ───── Conversazioni
  const selectConversation = useCallback((id:string)=>{ 
    const c=conversations.find(x=>x.id===id); 
    setViewMode('chat'); 
    setConversationId(id); 
    setMessages(c?.messages||[]); 
    setSavedMessages({}); setSavingMessages({}); setShowCopyFeedback({}); setShowSaveFeedback({});
  }, [conversations]);

  const renameConversation = useCallback((id:string)=>{ const c=conversations.find(x=>x.id===id); if(!c) return; const name=prompt('Rinomina chat', c.title); if(!name) return;
    setConversations(prev=>prev.map(x=>x.id===id?{...x,title:name.trim(),updatedAt:Date.now()}:x)); }, [conversations]);

  const renameMap = useCallback(async (id: string) => {
    const map = convertedFirebaseMaps.find(x => x.id === id);
    if (!map) return;
    const name = prompt('Rinomina mappa concettuale', map.name);
    if (!name) return;
    // Update Firebase map
    await updateConceptMap(id, { ...map.data, title: name.trim() });
    setRenamingMapId(null);
  }, [convertedFirebaseMaps, updateConceptMap]);

  const closeMap = useCallback((id: string) => {
    // Rimuovi la mappa dalle mappe aperte
    setOpenedMapIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
    // Se era selezionata, deselezionala
    if (selectedMapId === id) {
      setSelectedMapId(null);
    }
  }, [selectedMapId]);

  const deleteConversation = useCallback((id:string)=>{ const c=conversations.find(x=>x.id===id); if(!c) return;
    if(!confirm(`Eliminare la chat "${c.title}"?`)) return; const filtered=conversations.filter(x=>x.id!==id); setConversations(filtered);
    if(conversationId===id){ 
      if(filtered.length>0){ 
        const n=filtered[0]; setConversationId(n.id); setMessages(n.messages);
        setSavedMessages({}); setSavingMessages({}); setShowCopyFeedback({}); setShowSaveFeedback({});
      } else { 
        const n=makeConversationId(); setConversationId(n); setMessages([]);
        setSavedMessages({}); setSavingMessages({}); setShowCopyFeedback({}); setShowSaveFeedback({});
      } 
    }
  }, [conversations, conversationId]);

  // Funzione per copiare testo negli appunti
  const copyToClipboard = async (text: string, messageIndex: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setShowCopyFeedback({ ...showCopyFeedback, [messageIndex]: true });
      setTimeout(() => {
        setShowCopyFeedback(prev => ({ ...prev, [messageIndex]: false }));
      }, 2000);
      console.log('Testo copiato negli appunti');
    } catch (err) {
      console.error('Errore nel copiare il testo:', err);
    }
  };

  // Funzione per salvare manualmente una risposta AI
  const saveAIResponseToMemory = async (aiResponse: string, messageIndex: number, userMessage: string = '') => {
    // Prevenire doppi salvataggi
    if (savedMessages[messageIndex] || savingMessages[messageIndex]) {
      console.log('⚠️ Messaggio già salvato o in corso di salvataggio');
      return;
    }

    try {
      // Imposta come "in corso di salvataggio"
      setSavingMessages(prev => ({ ...prev, [messageIndex]: true }));

      console.log('🚀 Inizio salvataggio AI response:', {
        aiResponse: aiResponse.substring(0, 50) + '...',
        conversationId,
        userMessage: userMessage.substring(0, 30) + '...'
      });
      
      const response = await fetch('/api/memory/save-ai-response', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ai_response: aiResponse,
          conversation_id: conversationId,
          user_message: userMessage
        }),
      });
      
      console.log('📡 Response status:', response.status);
      console.log('📡 Response headers:', Object.fromEntries(response.headers.entries()));
      
      const responseText = await response.text();
      console.log('📡 Raw response text:', responseText);
      
      let result;
      try {
        result = JSON.parse(responseText);
      } catch (parseError) {
        console.error('❌ JSON parse error:', parseError);
        console.error('❌ Raw response that failed to parse:', responseText);
        throw new Error(`Failed to parse JSON: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`);
      }
      
      if (response.ok) {
        // Marca come salvato permanentemente
        setSavedMessages(prev => ({ ...prev, [messageIndex]: true }));
        
        setShowSaveFeedback({ ...showSaveFeedback, [messageIndex]: true });
        setTimeout(() => {
          setShowSaveFeedback(prev => ({ ...prev, [messageIndex]: false }));
        }, 2000);
        console.log('✅ Risposta AI salvata con successo:', result);
      } else {
        console.error('❌ Errore nel salvare la risposta AI:', result.error || result);
      }
    } catch (error) {
      console.error('❌ Errore generale nel salvare la risposta AI:', error);
    } finally {
      // Rimuovi "in corso di salvataggio"
      setSavingMessages(prev => ({ ...prev, [messageIndex]: false }));
    }
  };

  // ───── Submit con streaming (+ piano)
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (viewMode!=='chat') setViewMode('chat'); 
    if (!message.trim()) return;

    const userMessage: Message = { text: message, sender: 'user' };
    const historyPayload = [...messages, userMessage].map(m=>({role: m.sender==='user'?'user':'assistant', content: m.text}));
    setMessages(prev=>[...prev, userMessage]);

    const base = message.trim(); 
    setMessage(''); 
    setLoading(true);
    
    try {
      // Aggiungi messaggio AI vuoto che verrà riempito progressivamente
      setMessages(prev=>[...prev, {text:'', sender:'ai'}]);

      const projectName = selectedProject?.name || null;
      const contextFiles = selectedProject?.files || [];
      const mapContextText = buildMapContextText();

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minuti

      const endpoint = `${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://chatbot-cli-map-production.up.railway.app'}/api/chat`;
      console.log('Backend URL env var:', process.env.NEXT_PUBLIC_BACKEND_URL);
      console.log('Final endpoint:', endpoint);
      
      const res = await fetch(endpoint, {
        method:'POST', 
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          message: base,
          context_files: contextFiles,
          project_name: projectName,
          concept_map_context: mapContextText,
          active_concept_map_id: selectedMapId,
          history: historyPayload,
          conversation_id: conversationId,
          user_id: user?.uid // Add user ID for concept map retrieval
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      if(!res.ok) throw new Error('Network response was not ok');

      const reader = res.body?.getReader(); 
      const decoder=new TextDecoder();
      if(reader){ 
        setIsStreaming(true);
        let answerAcc='';
        let lastUpdateTime = 0;
        while(true){ 
          const {done, value}=await reader.read(); 
          if(done) break;
          const chunk=decoder.decode(value,{stream:true});
          answerAcc += chunk;
          
          // Throttle updates for smoother rendering (max 60fps)
          const now = Date.now();
          if (now - lastUpdateTime > 16 || done) {
            setMessages(prev=>{ 
              const nm=[...prev]; 
              const i=nm.length-1; 
              if(i>=0 && nm[i].sender==='ai'){ 
                nm[i]={...nm[i], text: answerAcc}; 
              } 
              return nm; 
            });
            lastUpdateTime = now;
          }
        }
        
        // Final update to ensure we have the complete response
        setMessages(prev=>{ 
          const nm=[...prev]; 
          const i=nm.length-1; 
          if(i>=0 && nm[i].sender==='ai'){ 
            nm[i]={...nm[i], text: answerAcc}; 
          } 
          return nm; 
        });
        setIsStreaming(false);
      }
    } catch (err:any){
      if (err.name === 'AbortError') {
        setMessages(prev=>{ 
          const nm=[...prev]; 
          if(nm.length && nm[nm.length-1].sender==='ai' && nm[nm.length-1].text==='') 
            nm.pop(); 
          return [...nm,{text:`Error: Chat timeout (2 minutes)`, sender:'ai'}]; 
        });
      } else {
        setMessages(prev=>{ 
          const nm=[...prev]; 
          if(nm.length && nm[nm.length-1].sender==='ai' && nm[nm.length-1].text==='') 
            nm.pop(); 
          return [...nm,{text:`Error: ${err?.message||err}`, sender:'ai'}]; 
        });
      }
    } finally { 
      setLoading(false);
      setIsStreaming(false);
    }
  }, [message, messages, viewMode, selectedProject, buildMapContextText, conversationId]);

  // ───── UI
  return (
    <div className="flex w-full h-full" style={{ backgroundColor: '#ffffff' }}>
      {/* Sidebar */}
      <div className="w-64 p-4 flex flex-col" style={{ backgroundColor: '#f9fbff' }}>
        <h2 className="text-xl font-bold mb-6 flex items-center text-gray-800">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 mr-2"><path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2 2 0 0 1 5.25 6H10" /></svg>
          ChatMap
        </h2>

        <div className="mb-6">
          <button className={`w-full flex items-center p-2 rounded transition-colors text-gray-700 ${viewMode==='chat'?'bg-gray-200':'hover:bg-gray-200'}`} onClick={()=>{ setViewMode('chat'); const id=makeConversationId(); setConversationId(id); setMessages([]); setSavedMessages({}); setSavingMessages({}); setShowCopyFeedback({}); setShowSaveFeedback({}); }} title="Nuova chat">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-2"><path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Nuova chat
          </button>
          <div className="mt-2 text-[11px] text-gray-500">ID conversazione: <span className="font-mono">{conversationId.slice(0,8)}…</span></div>
        </div>

        <div className="space-y-4">
          {/* Mappe concettuali */}
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Mappe concettuali</h3>
            <div className="space-y-1">
              <button className={`w-full text-left p-2 rounded transition-colors ${viewMode==='map'?'bg-blue-100 text-blue-700':'hover:bg-gray-200 text-gray-700'}`} onClick={()=>{
                setViewMode('map');
                // Mostra tutte le mappe nascoste quando si apre la vista mappe
                setHiddenMapIds(new Set());
                // Deseleziona la mappa corrente per mostrare la vista panoramica
                setSelectedMapId(null);
              }}>Apri mappe concettuali</button>
              <button onClick={createNewConceptMap} className="w-full text-left p-2 rounded bg-blue-500 text-white hover:bg-blue-600 transition-colors">+ Nuova mappa concettuale</button>
            </div>
            <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
              {visibleMapsInSidebar.length===0 && <div className="text-xs text-gray-400 p-2 italic">Nessuna mappa aperta</div>}
              {visibleMapsInSidebar.map(m=>(
                <div key={m.id} className={`flex items-center justify-between w-full p-2 rounded text-sm transition-colors ${selectedMapId===m.id?'bg-blue-100 text-blue-700':'hover:bg-gray-200 text-gray-700'}`}>
                  <button 
                    className="flex-1 text-left" 
                    onClick={()=>{ setSelectedMapId(m.id); setViewMode('map'); }} 
                    onDoubleClick={()=>renameMap(m.id)}
                    title={new Date(m.updatedAt).toLocaleString()}
                  >
                    {m.name}
                  </button>
                  <div className="flex items-center ml-2">
                    <button className="p-1 rounded hover:bg-gray-50 text-gray-600" title="Chiudi mappa" onClick={(e)=>{e.stopPropagation(); closeMap(m.id);}}>✖</button>
                    <button className="ml-1 p-1 rounded hover:bg-red-50 text-red-600" title="Elimina mappa" onClick={async (e)=>{e.stopPropagation(); if(!confirm(`Eliminare la mappa "${m.name}"?`)) return; 
                      // Delete from Firebase
                      await deleteConceptMap(m.id);
                      // Remove from opened maps
                      setOpenedMapIds(prev => {
                        const newSet = new Set(prev);
                        newSet.delete(m.id);
                        return newSet;
                      });
                      if(selectedMapId===m.id) setSelectedMapId(null);}}>🗑</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Progetti */}
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Progetti</h3>
            <div className="flex mb-2">
              <input type="text" value={newProjectName} onChange={e=>setNewProjectName(e.target.value)} placeholder="Nome progetto" className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded-l focus:outline-none focus:ring-1 focus:ring-blue-500" onKeyDown={e=>e.key==='Enter' && createNewProject()} />
              <button onClick={createNewProject} className="px-2 py-1 bg-blue-500 text-white text-sm rounded-r hover:bg-blue-600 transition-colors">+</button>
            </div>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {projects.map(project=>(
                <div key={project.id}>
                  <div className={`w-full text-left p-2 rounded transition-colors flex items-center justify-between ${selectedProjectId===project.id?'bg-blue-100 text-blue-700':'hover:bg-gray-200 text-gray-700'}`}>
                    <button className="flex-1 text-left" onClick={()=>setSelectedProjectId(project.id)}>{project.name}</button>
                    {selectedProjectId===project.id && (
                      <button onClick={(e)=>{e.stopPropagation(); toggleAutoCapture(project.id);}} className={`ml-2 px-2 py-0.5 text-xs rounded-full transition-all ${project.autoCapture?'bg-green-500 text-white':'bg-gray-300 text-gray-600'}`} title={project.autoCapture?'Auto-capture attivo':'Auto-capture disattivato'}>
                        {project.autoCapture ? '🎯 Auto' : 'Manual'}
                      </button>
                    )}
                  </div>
                  {selectedProjectId===project.id && (
                    <div className="ml-2 mt-1 space-y-1">
                      {project.files.length>0 ? renderTree(buildFileTree(project.files)) : (
                        <div className="text-xs text-gray-400 p-1 italic">{project.autoCapture?'🎯 Clicca sui code block per salvare':'Nessun file'}</div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              {projects.length===0 && <div className="text-xs text-gray-400 p-2 italic">Nessun progetto</div>}
            </div>
          </div>

          {/* Chat: storico */}
          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Chat</h3>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {conversations.length===0 && <div className="text-xs text-gray-400 p-2 italic">Nessuna chat</div>}
              {conversations.map(c=>{
                const isActive=c.id===conversationId;
                return (
                  <div key={c.id} className={`flex items-center justify-between w-full p-2 rounded text-sm transition-colors ${isActive?'bg-blue-100 text-blue-700':'hover:bg-gray-200 text-gray-700'}`}>
                    <button className="flex-1 text-left" onClick={()=>selectConversation(c.id)} title={new Date(c.updatedAt).toLocaleString()}>
                      <div className="truncate font-medium">{c.title || 'Nuova chat'}</div>
                      <div className="text-[10px] opacity-75">{new Date(c.updatedAt).toLocaleString()}</div>
                    </button>
                    <div className="flex items-center ml-2">
                      <button className="p-1 rounded hover:bg-gray-300" title="Rinomina chat" onClick={(e)=>{e.stopPropagation(); renameConversation(c.id);}}>✏️</button>
                      <button className="p-1 rounded hover:bg-red-50 text-red-600 ml-1" title="Elimina chat" onClick={(e)=>{e.stopPropagation(); deleteConversation(c.id);}}>🗑</button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-auto border-t border-gray-200 pt-3">
          <div className="flex items-center justify-between p-2">
            <div className="flex items-center space-x-2 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                <span className="text-sm text-white">👤</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs text-gray-500 truncate">{user?.email || 'Utente'}</div>
              </div>
            </div>
            <div className="relative settings-menu-container">
              <button 
                onClick={() => setShowSettingsMenu(!showSettingsMenu)}
                className="bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 text-xs rounded transition-colors flex-shrink-0"
                title="Impostazioni"
              >
                ⚙️
              </button>
              
              {showSettingsMenu && (
                <div className="absolute bottom-full right-0 mb-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50">
                  <button
                    onClick={() => {
                      setShowSettingsMenu(false);
                      // TODO: Navigate to profile
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                  >
                    <span>👤</span>
                    <span>Profilo</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      setShowSettingsMenu(false);
                      // TODO: Navigate to settings
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                  >
                    <span>⚙️</span>
                    <span>Impostazioni</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      setShowSettingsMenu(false);
                      setShowMemoryDashboard(true);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                  >
                    <span>🧠</span>
                    <span>Memorie</span>
                  </button>
                  
                  <button
                    onClick={() => {
                      setViewMode(viewMode === 'chat' ? 'map' : 'chat');
                      setShowSettingsMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
                  >
                    <span>{viewMode === 'chat' ? '🗺️' : '💬'}</span>
                    <span>Layout: {viewMode === 'chat' ? 'Mappe' : 'Chat'}</span>
                  </button>
                  
                  <hr className="my-1" />
                  
                  <button
                    onClick={() => {
                      setShowSettingsMenu(false);
                      // TODO: Navigate to delete account
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                  >
                    <span>🗑️</span>
                    <span>Cancella Account</span>
                  </button>
                  
                  <hr className="my-1" />
                  
                  <button
                    onClick={() => {
                      setShowSettingsMenu(false);
                      logout();
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                  >
                    <span>🚪</span>
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col">
        {viewMode==='map' ? (
          <div className="flex-1 overflow-hidden">
            {selectedMap ? (
              <ConceptMapPreview data={selectedMap.data} onChange={(next)=>{ if(!selectedMapId) return; handleMapChange(selectedMapId, next); }} onCopyContext={()=>showToast('📋 Contesto mappa copiato','success')} conversationId={conversationId} />
            ) : allVisibleMaps.length > 0 ? (
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="max-w-4xl mx-auto">
                  <h2 className="text-2xl font-bold mb-6 text-gray-800">Le tue Mappe Concettuali</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {allVisibleMaps.map(m => (
                      <div key={m.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => { 
                          setSelectedMapId(m.id); 
                          // Add the map to "opened" maps
                          setOpenedMapIds(prev => new Set([...prev, m.id]));
                        }}
                      >
                        <h3 className="font-semibold text-gray-800 mb-2 truncate">{m.name}</h3>
                        <div className="text-xs text-gray-500 mb-3">
                          {m.data.nodes.length} nodi • {m.data.edges.length} collegamenti
                        </div>
                        <div className="text-xs text-gray-400">
                          {new Date(m.updatedAt).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6">
                    <button onClick={createNewConceptMap} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                      + Crea Nuova Mappa Concettuale
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
                <p className="text-sm">Nessuna mappa concettuale disponibile.</p>
                <button onClick={createNewConceptMap} className="mt-3 px-3 py-1.5 rounded bg-blue-500 text-white hover:bg-blue-600">+ Crea una mappa concettuale</button>
              </div>
            )}
          </div>
        ) : (
          <>
            <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 flex justify-center" style={{ contain:'strict' }}>
              <div className="w-full max-w-4xl space-y-4">
                {messages.length===0 ? (
                  <div className="text-center text-gray-500 mt-10">
                    <div className="mb-4">
                      <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-lg">Benvenuto in ChatMap!</p>
                      <p className="text-sm mt-2">Inizia una conversazione scrivendo un messaggio qui sotto.</p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, i) => {
                    // Funzione per pulire il testo dal blocco di ragionamento
                    const cleanText = (text: string) => {
                      const reasoningRegex = /\[REASONING_START\][\s\S]*?\[REASONING_END\]\s*/;
                      return text.replace(reasoningRegex, '').trim();
                    };

                    return (
                      <div key={i}>
                        <div className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                          {msg.sender === 'user' ? (
                            <div className="max-w-[85%] p-3 bg-blue-500 text-white rounded-lg rounded-br-none">
                              {msg.text}
                            </div>
                          ) : (
                            <div className="max-w-[85%] p-3 text-gray-800 relative group">
                              <div className="prose prose-sm max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                                  {cleanText(msg.text)}
                                </ReactMarkdown>
                              </div>
                              {loading && msg.text === '' && (
                                <span className="inline-block ml-1">
                                  <span className="animate-pulse">●</span>
                                  <span className="animate-pulse delay-75">●</span>
                                  <span className="animate-pulse delay-150">●</span>
                                </span>
                              )}
                              
                              {/* Pulsanti per messaggi AI completati */}
                              {!loading && msg.text && (
                                <div className="flex gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                                  <button
                                    onClick={() => copyToClipboard(cleanText(msg.text), i)}
                                    className={`flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors ${
                                      showCopyFeedback[i] 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-gray-100 hover:bg-gray-200 text-gray-600 hover:text-gray-800'
                                    }`}
                                    title="Copia negli appunti"
                                  >
                                    {showCopyFeedback[i] ? (
                                      <>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        Copiato!
                                      </>
                                    ) : (
                                      <>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                        Copia
                                      </>
                                    )}
                                  </button>
                                  
                                  <button
                                    onClick={() => {
                                      // Trova il messaggio utente precedente per il contesto
                                      const userMessage = i > 0 && messages[i-1]?.sender === 'user' ? messages[i-1].text : '';
                                      saveAIResponseToMemory(cleanText(msg.text), i, userMessage);
                                    }}
                                    disabled={savedMessages[i] || savingMessages[i]}
                                    className={`flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors ${
                                      savedMessages[i]
                                        ? 'bg-green-300 text-green-900 cursor-default'
                                        : savingMessages[i]
                                        ? 'bg-yellow-100 text-yellow-800 cursor-wait'
                                        : showSaveFeedback[i]
                                        ? 'bg-green-200 text-green-800'
                                        : 'bg-green-100 hover:bg-green-200 text-green-600 hover:text-green-800'
                                    }`}
                                    title={savedMessages[i] ? "Già salvato" : savingMessages[i] ? "Salvataggio in corso..." : "Salva in memoria"}
                                  >
                                    {savedMessages[i] ? (
                                      <>
                                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                                          <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                                        </svg>
                                        Salvato
                                      </>
                                    ) : savingMessages[i] ? (
                                      <>
                                        <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                        </svg>
                                        Salvando...
                                      </>
                                    ) : showSaveFeedback[i] ? (
                                      <>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        Salvato!
                                      </>
                                    ) : (
                                      <>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Salva
                                      </>
                                    )}
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input */}
            <div className="p-4 flex justify-center">
              <div className="w-full max-w-4xl">
                <form onSubmit={handleSubmit} className="rounded-xl shadow-md border border-gray-200 p-3 flex flex-col" style={{backgroundColor:'#f3f4f6'}}>
                  <input type="text" value={message} onChange={e=>setMessage(e.target.value)} placeholder="Scrivi un messaggio..." className="w-full px-2 py-3 bg-transparent focus:outline-none" disabled={loading} />
                  <div className="flex flex-wrap gap-3 justify-between items-center mt-2">
                    <div className="flex items-center gap-2">
                      <button type="submit" disabled={loading||!message.trim()} className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50">
                        {loading ? (isStreaming ? '📡 Streaming...' : 'Invio...') : 'Invia'}
                      </button>
                      
                      {/* Simplified interface - no multi-agent toggle */}
                    </div>
                  </div>
                  <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                    <div>
                      {selectedProject && <span className={`flex items-center ${selectedProject.autoCapture?'text-green-600':'text-gray-500'}`}>{selectedProject.autoCapture?'🎯 Auto-capture attivo':'📁'} {selectedProject.name}</span>}
                      {selectedMap && <div className="text-[11px]">🗺️ Mappa attiva nel contesto: <span className="font-semibold">{selectedMap.name}</span></div>}
                    </div>
                    <div className="flex items-center space-x-2">
                      {/* System Status */}
                      <span className="text-[10px] flex items-center text-blue-600">
                        ⚡ GLM 4.5
                      </span>
                      
                      {memoryChecked && (
                        <span className={`text-[10px] flex items-center ${memoryAvailable ? 'text-green-600' : 'text-gray-400'}`}>
                          {memoryAvailable ? '🧠 Memoria attiva' : '🧠 Memoria non disponibile'}
                        </span>
                      )}
                    </div>
                  </div>
                </form>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modale file */}
      {isFileModalOpen && currentFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b">
              <h3 className="text-lg font-semibold text-gray-800">{currentFile.path}</h3>
              <button onClick={closeFileModal} className="text-gray-500 hover:text-gray-700">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <CodeBlock language={currentFile.language} inline={false} className={`language-${currentFile.language}`}>{currentFile.content}</CodeBlock>
            </div>
            <div className="flex justify-end p-4 border-t">
              <button onClick={closeFileModal} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Chiudi</button>
            </div>
          </div>
        </div>
      )}

      {/* Error console */}
      <button onClick={()=>setIsErrorConsoleOpen(true)} className="fixed bottom-6 right-6 bg-red-500 text-white p-3 rounded-full shadow-lg hover:bg-red-600 z-40" title="Apri console di sviluppo">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
      </button>
      <ErrorConsole isVisible={isErrorConsoleOpen} onClose={()=>setIsErrorConsoleOpen(false)} />
      
      {/* Memory Dashboard */}
      {showMemoryDashboard && (
        <MemoryDashboard onClose={() => setShowMemoryDashboard(false)} />
      )}
    </div>
  );
}
