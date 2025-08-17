"use client";
import { useCallback, useEffect, useMemo, useRef, useState, useId } from "react";
import { useFirebaseConceptMaps } from '../lib/useFirebaseConceptMaps';
import { useAuth } from '../lib/AuthContext';

export type RelationType = 
  | "causes" // causa → effetto
  | "is_a" // è un/una → categoria
  | "part_of" // parte di → intero
  | "has" // possiede → proprietà
  | "needs" // richiede → prerequisito
  | "solves" // risolve → problema
  | "uses" // utilizza → strumento
  | "leads_to" // porta a → risultato
  | "similar_to" // simile a → analogia
  | "opposite_to" // opposto a → contrasto
  | "depends_on" // dipende da → dipendenza
  | "creates" // crea → output
  | "generic"; // collegamento generico

export interface ConceptNode { id: string; label: string; x: number; y: number }
export interface ConceptEdge { 
  id: string; 
  from: string; 
  to: string; 
  curveSide?: 1 | -1;
  relationshipType?: RelationType;
  label?: string; // etichetta opzionale per la relazione
}
export interface ConceptMapData { title?: string; nodes: ConceptNode[]; edges: ConceptEdge[] }

interface Props { 
  data: ConceptMapData; 
  onChange?: (next: ConceptMapData) => void; 
  onCopyContext?: (text: string) => void;
  conversationId?: string; // For auto-saving to reasoning system
}


// Dynamic node sizing - replaced fixed dimensions with CSS
const MIN_NODE_W = 120;  // Minimum width
const MAX_NODE_W = 350;  // Maximum width  
const MIN_NODE_H = 60;   // Minimum height
const DEFAULT_NODE_W = 200; // Default for calculations (backward compatibility)
const DEFAULT_NODE_H = 80;  // Default for calculations (backward compatibility)

// ===== Relationship types styling =====
const RELATIONSHIP_STYLES: Record<RelationType, { color: string; icon: string; label: string; description: string }> = {
  causes: { color: "#dc2626", icon: "➤", label: "Causa", description: "causa → effetto" },
  is_a: { color: "#2563eb", icon: "⊂", label: "È un/una", description: "è un/una → categoria" },
  part_of: { color: "#7c3aed", icon: "∈", label: "Parte di", description: "parte di → intero" },
  has: { color: "#059669", icon: "◈", label: "Possiede", description: "possiede → proprietà" },
  needs: { color: "#d97706", icon: "⚡", label: "Richiede", description: "richiede → prerequisito" },
  solves: { color: "#16a34a", icon: "✓", label: "Risolve", description: "risolve → problema" },
  uses: { color: "#0891b2", icon: "⚙", label: "Utilizza", description: "utilizza → strumento" },
  leads_to: { color: "#c026d3", icon: "→", label: "Porta a", description: "porta a → risultato" },
  similar_to: { color: "#65a30d", icon: "≈", label: "Simile a", description: "simile a → analogia" },
  opposite_to: { color: "#e11d48", icon: "≠", label: "Opposto a", description: "opposto a → contrasto" },
  depends_on: { color: "#f59e0b", icon: "⟸", label: "Dipende da", description: "dipende da → dipendenza" },
  creates: { color: "#8b5cf6", icon: "✦", label: "Crea", description: "crea → output" },
  generic: { color: "#6b7280", icon: "―", label: "Generico", description: "collegamento generico" }
};

// ===== Edge/Arrow settings =====
const EDGE_GAP_BASE = 16;
const NODE_SHADOW_PAD = 10;
const EDGE_GAP_START = 0;
const EDGE_GAP_END   = EDGE_GAP_BASE + NODE_SHADOW_PAD;

const EDGE_HIT_WIDTH = 14;
const EDGE_BASE_COLOR = "#6b7280";
const EDGE_SELECTED_COLOR = "#3b82f6";
const EDGE_STYLE: "curved" | "straight" | "orthogonal" = "curved";
const CURVE_STRENGTH = 0.3;

// Arrowhead shape
const HEAD_LEN = 12;
const HEAD_HALF = 6;

// ===== Geometry helpers =====
interface Point { x: number; y: number } 
interface Rect { x: number; y: number; w: number; h: number }

const centerOfNode = (n:ConceptNode):Point=>({x:n.x+DEFAULT_NODE_W/2,y:n.y+DEFAULT_NODE_H/2});
const rectOfNode   = (n:ConceptNode):Rect=>({x:n.x,y:n.y,w:DEFAULT_NODE_W,h:DEFAULT_NODE_H});

function pointInRect(p: Point, r: Rect){
  return p.x >= r.x && p.x <= r.x + r.w && p.y >= r.y && p.y <= r.y + r.h;
}

// Intersezione segmento p1->p2 con rect.
function lineRectIntersection(p1:Point,p2:Point,rect:Rect):Point|null{
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) return p1;
  let tmin = 0, tmax = 1;

  if (Math.abs(dx) > 0.01) {
    const tx1 = (rect.x - p1.x) / dx;
    const tx2 = (rect.x + rect.w - p1.x) / dx;
    const txmin = Math.min(tx1, tx2), txmax = Math.max(tx1, tx2);
    tmin = Math.max(tmin, txmin);
    tmax = Math.min(tmax, txmax);
  } else if (p1.x < rect.x || p1.x > rect.x + rect.w) return null;

  if (Math.abs(dy) > 0.01) {
    const ty1 = (rect.y - p1.y) / dy;
    const ty2 = (rect.y + rect.h - p1.y) / dy;
    const tymin = Math.min(ty1, ty2), tymax = Math.max(ty1, ty2);
    tmin = Math.max(tmin, tymin);
    tmax = Math.min(tmax, tymax);
  } else if (p1.y < rect.y || p1.y > rect.y + rect.h) return null;

  if (tmin > tmax) return null;

  const inside = pointInRect(p1, rect);
  const t = inside ? tmax : tmin;
  const tt = Math.max(0, Math.min(1, t));
  return { x: p1.x + tt * dx, y: p1.y + tt * dy };
}

function addGapFromRect(pOnRect:Point, fromCenter:Point, gap:number):Point{
  const dx=pOnRect.x-fromCenter.x, dy=pOnRect.y-fromCenter.y;
  const dist=Math.hypot(dx,dy);
  if(dist < 0.01) return pOnRect;
  const nx=dx/dist, ny=dy/dist;
  return { x:pOnRect.x + nx*gap, y:pOnRect.y + ny*gap };
}

function computeAnchors(fromNode:ConceptNode, toNode:ConceptNode, gapStart=EDGE_GAP_START, gapEnd=EDGE_GAP_END){
  const fromCenter=centerOfNode(fromNode);
  const toCenter=centerOfNode(toNode);
  const startOnRect=lineRectIntersection(fromCenter,toCenter,rectOfNode(fromNode)) || fromCenter;
  const endOnRect  =lineRectIntersection(toCenter,fromCenter,rectOfNode(toNode)) || toCenter;
  const start=addGapFromRect(startOnRect,fromCenter,gapStart);
  const end  =addGapFromRect(endOnRect,toCenter,gapEnd);
  const dx=end.x-start.x, dy=end.y-start.y, dist=Math.hypot(dx,dy);
  return { start, end, dx, dy, dist, fromCenter, toCenter };
}

// Curva con tangenti RADIALI
function buildCurvedPathRadial(
  start: Point, end: Point, fromCenter: Point, toCenter: Point, side: 1|-1
){
  const dx = end.x - start.x, dy = end.y - start.y;
  const dist = Math.hypot(dx, dy) || 1;

  const h = Math.min(dist * CURVE_STRENGTH, 80);
  const startDir = { x: (start.x - fromCenter.x), y: (start.y - fromCenter.y) };
  let sLen = Math.hypot(startDir.x, startDir.y) || 1;
  startDir.x /= sLen; startDir.y /= sLen;

  const endDir = { x: (toCenter.x - end.x), y: (toCenter.y - end.y) };
  let eLen = Math.hypot(endDir.x, endDir.y) || 1;
  endDir.x /= eLen; endDir.y /= eLen;

  const vnx = -dy/dist, vny = dx/dist;
  const lateral = Math.min(dist * 0.18, 56) * side;

  const cp1 = { x: start.x + startDir.x*h + vnx*lateral,
                y: start.y + startDir.y*h + vny*lateral };
  const cp2 = { x: end.x   - endDir.x*h,
                y: end.y   - endDir.y*h };
  const path = `M ${start.x} ${start.y} C ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${end.x} ${end.y}`;
  return { path, headDir: endDir };
}

const buildStraightPath=(s:Point,e:Point)=>`M ${s.x} ${s.y} L ${e.x} ${e.y}`;
const buildOrthogonalPath=(s:Point,e:Point)=>{
  const mx=(s.x+e.x)/2;
  return `M ${s.x} ${s.y} L ${mx} ${s.y} L ${mx} ${e.y} L ${e.x} ${e.y}`;
};
const pathMid=(s:Point,e:Point):Point=>({x:(s.x+e.x)/2,y:(s.y+e.y)/2});

function determineCurveSide(fromNode: ConceptNode, toNode: ConceptNode): 1 | -1 {
  const dx = toNode.x - fromNode.x, dy = toNode.y - fromNode.y;
  return Math.abs(dx) > Math.abs(dy) ? (dx >= 0 ? 1 : -1) : (dy >= 0 ? 1 : -1);
}

export default function ConceptMapPreview({ data, onChange, onCopyContext, conversationId }: Props){
  const { user } = useAuth();
  const { saveConceptMap, updateConceptMap, deleteConceptMap, conceptMaps, fetchConceptMaps } = useFirebaseConceptMaps();
  const [currentMapId, setCurrentMapId] = useState<string | null>(null);
  const [mapData,setMapData]=useState<ConceptMapData>(data);
  const [isManagingMapsInternally, setIsManagingMapsInternally] = useState(false);
  
  // Only sync with external data when not managing maps internally
  useEffect(() => {
    if (!isManagingMapsInternally) {
      setMapData(data);
    }
  }, [data, isManagingMapsInternally]);
  const containerRef=useRef<HTMLDivElement>(null);
  const canvasRef=useRef<HTMLDivElement>(null);
  const [dragId,setDragId]=useState<string|null>(null);
  const dragOffset=useRef<{dx:number;dy:number}>({dx:0,dy:0});
  const dragSelectionRef=useRef<Set<string>>(new Set());
  const dragStartRef=useRef<{mx:number;my:number;positions:Map<string,{x:number;y:number}>}|null>(null);
  const [linkMode,setLinkMode]=useState(false);
  const [linkFromId,setLinkFromId]=useState<string|null>(null);
  const [cursorPos,setCursorPos]=useState<Point|null>(null);
  const [spaceActive,setSpaceActive]=useState(false);
  const [isPanning,setIsPanning]=useState(false);
  const [pan,setPan]=useState<Point>({x:0,y:0});
  const panStartRef=useRef<{x:number;y:number;panX:number;panY:number}|null>(null);
  const [selectedId,setSelectedId]=useState<string|null>(null);
  const [editingId,setEditingId]=useState<string|null>(null);
  const [showNodeMenu,setShowNodeMenu]=useState<Point|null>(null);
  const [selectedEdgeId,setSelectedEdgeId]=useState<string|null>(null);
  const [curveSignGlobal,setCurveSignGlobal]=useState<1|-1>(1);
  const [connectionDragStartId, setConnectionDragStartId] = useState<string | null>(null);
  const [showRelationshipMenu, setShowRelationshipMenu] = useState<{x: number; y: number; fromId: string; toId: string} | null>(null);
  const [selectedRelationshipType, setSelectedRelationshipType] = useState<RelationType>("generic");
  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const [lastSaveStatus, setLastSaveStatus] = useState<'saved' | 'saving' | 'error' | null>(null);
  const [showHistoricalMaps, setShowHistoricalMaps] = useState(false);
  const [selectedMapsForDeletion, setSelectedMapsForDeletion] = useState<Set<string>>(new Set());
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<{type: 'single' | 'multiple' | 'all', mapId?: string, mapTitle?: string} | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [renamingMapId, setRenamingMapId] = useState<string | null>(null);
  const [tempTitle, setTempTitle] = useState('');
  const [renamingMainTitle, setRenamingMainTitle] = useState(false);
  const [tempMainTitle, setTempMainTitle] = useState('');
  const lastClickTimeRef = useRef(0);
  const lastSavedDataRef = useRef<string>('');
  // Per prevenire inizio panning during doppio click
  
  // Archive functionality

  useId();

  // Auto-save to Firebase
  const autoSaveToFirebase = useCallback(async (mapDataToSave: ConceptMapData) => {
    if (!user || isAutoSaving) return;
    
    // Only auto-save if there are nodes and edges (meaningful content)
    if (mapDataToSave.nodes.length === 0) return;
    
    // Check if data actually changed from last save
    const currentDataString = JSON.stringify(mapDataToSave);
    if (currentDataString === lastSavedDataRef.current) {
      return;
    }
    
    setIsAutoSaving(true);
    setLastSaveStatus('saving');
    
    try {
      if (currentMapId) {
        // Update existing map
        const success = await updateConceptMap(currentMapId, mapDataToSave);
        if (success) {
          setLastSaveStatus('saved');
          console.log(`🔥 Updated concept map in Firebase: ${currentMapId}`);
        } else {
          throw new Error('Failed to update Firebase');
        }
      } else {
        // Create new map
        const mapId = await saveConceptMap(mapDataToSave);
        if (mapId) {
          setCurrentMapId(mapId);
          setLastSaveStatus('saved');
          console.log(`🔥 Created new concept map in Firebase: ${mapId}`);
        } else {
          throw new Error('Failed to save to Firebase');
        }
      }
      
      // Clear saved status after 3 seconds
      setTimeout(() => setLastSaveStatus(null), 3000);
      
    } catch (error) {
      console.error('Failed to auto-save concept map:', error);
      setLastSaveStatus('error');
      setTimeout(() => setLastSaveStatus(null), 5000);
    } finally {
      setIsAutoSaving(false);
    }
  }, [user, saveConceptMap, updateConceptMap, currentMapId, isAutoSaving]);

  // Auto-save when mapData changes (debounced) - only if data actually changed
  // Only auto-save if we're managing maps internally (not when controlled by parent)
  useEffect(() => {
    if (!user || !isManagingMapsInternally) return;
    
    const currentDataString = JSON.stringify(mapData);
    
    // Only save if data actually changed
    if (currentDataString === lastSavedDataRef.current) {
      return;
    }
    
    const saveTimer = setTimeout(() => {
      autoSaveToFirebase(mapData);
      lastSavedDataRef.current = currentDataString;
    }, 3000); // 3 second debounce for Firebase
    
    return () => clearTimeout(saveTimer);
  }, [mapData, autoSaveToFirebase, user, isManagingMapsInternally]);

  // Load historical concept map
  const loadHistoricalMap = useCallback((mapId: string, mapData: ConceptMapData) => {
    setIsManagingMapsInternally(true);
    setCurrentMapId(mapId);
    setMapData(mapData);
    onChange?.(mapData);
    setShowHistoricalMaps(false);
    // Update the reference so we don't auto-save immediately
    lastSavedDataRef.current = JSON.stringify(mapData);
  }, [onChange]);

  // Create new concept map
  const createNewMap = useCallback(() => {
    const newMapData: ConceptMapData = {
      title: 'Nuova Mappa Concettuale',
      nodes: [],
      edges: []
    };
    setIsManagingMapsInternally(true);
    setCurrentMapId(null);
    setMapData(newMapData);
    onChange?.(newMapData);
    setShowHistoricalMaps(false);
    lastSavedDataRef.current = '';
  }, [onChange]);

  // Close current map (without deleting)
  const closeCurrentMap = useCallback(() => {
    createNewMap();
    setShowHistoricalMaps(false);
  }, [createNewMap]);

  // Close any map (load from dropdown)
  const closeMap = useCallback((mapId: string) => {
    // If closing current map, create new map
    if (currentMapId === mapId) {
      createNewMap();
    }
    // Always close the dropdown
    setShowHistoricalMaps(false);
  }, [currentMapId, createNewMap]);

  // Start renaming a map
  const startRenaming = useCallback((mapId: string, currentTitle: string) => {
    setRenamingMapId(mapId);
    setTempTitle(currentTitle || 'Mappa Senza Titolo');
  }, []);

  // Confirm rename
  const confirmRename = useCallback(async (mapId: string) => {
    if (!tempTitle.trim()) {
      setRenamingMapId(null);
      return;
    }

    try {
      const success = await updateConceptMap(mapId, { title: tempTitle.trim() });
      if (success) {
        // Update current map title if it's the active one
        if (currentMapId === mapId) {
          setIsManagingMapsInternally(true);
          setMapData(prev => ({ ...prev, title: tempTitle.trim() }));
          onChange?.({ ...mapData, title: tempTitle.trim() });
        }
        // Refresh maps list
        await fetchConceptMaps();
      }
    } catch (error) {
      console.error('Failed to rename map:', error);
    } finally {
      setRenamingMapId(null);
      setTempTitle('');
    }
  }, [tempTitle, updateConceptMap, currentMapId, mapData, onChange, fetchConceptMaps]);

  // Cancel rename
  const cancelRename = useCallback(() => {
    setRenamingMapId(null);
    setTempTitle('');
  }, []);

  // Delete single concept map
  const deleteSingleMap = useCallback(async (mapId: string, mapTitle: string) => {
    setShowDeleteConfirm({ type: 'single', mapId, mapTitle });
  }, []);

  // Delete multiple concept maps
  const deleteSelectedMaps = useCallback(async () => {
    if (selectedMapsForDeletion.size === 0) return;
    setShowDeleteConfirm({ type: 'multiple' });
  }, [selectedMapsForDeletion]);

  // Delete all concept maps
  const deleteAllMaps = useCallback(async () => {
    if (conceptMaps.length === 0) return;
    setShowDeleteConfirm({ type: 'all' });
  }, [conceptMaps.length]);

  // Confirm deletion
  const confirmDeletion = useCallback(async () => {
    if (!showDeleteConfirm || isDeleting) return;
    
    setIsDeleting(true);
    
    try {
      if (showDeleteConfirm.type === 'single' && showDeleteConfirm.mapId) {
        await deleteConceptMap(showDeleteConfirm.mapId);
        // If deleting current map, reset to new map
        if (currentMapId === showDeleteConfirm.mapId) {
          createNewMap();
        }
      } else if (showDeleteConfirm.type === 'multiple') {
        // Delete all selected maps
        const promises = Array.from(selectedMapsForDeletion).map(mapId => deleteConceptMap(mapId));
        await Promise.all(promises);
        // If current map was deleted, reset to new map
        if (currentMapId && selectedMapsForDeletion.has(currentMapId)) {
          createNewMap();
        }
        setSelectedMapsForDeletion(new Set());
      } else if (showDeleteConfirm.type === 'all') {
        // Delete all maps
        const promises = conceptMaps.map(map => deleteConceptMap(map.id!));
        await Promise.all(promises);
        createNewMap();
      }
      
      // Refresh the maps list
      await fetchConceptMaps();
      
    } catch (error) {
      console.error('Failed to delete concept maps:', error);
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(null);
    }
  }, [showDeleteConfirm, isDeleting, deleteConceptMap, currentMapId, selectedMapsForDeletion, conceptMaps, createNewMap, fetchConceptMaps]);

  // Toggle map selection for deletion
  const toggleMapSelection = useCallback((mapId: string) => {
    setSelectedMapsForDeletion(prev => {
      const newSet = new Set(prev);
      if (newSet.has(mapId)) {
        newSet.delete(mapId);
      } else {
        newSet.add(mapId);
      }
      return newSet;
    });
  }, []);

  // Select all maps
  const selectAllMaps = useCallback(() => {
    setSelectedMapsForDeletion(new Set(conceptMaps.map(map => map.id!)));
  }, [conceptMaps]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedMapsForDeletion(new Set());
  }, []);


  useEffect(()=>{
    const kd=(e:KeyboardEvent)=>{ if(e.key===" ") setSpaceActive(true)};
    const ku=(e:KeyboardEvent)=>{ if(e.key===" ") setSpaceActive(false)};
    window.addEventListener("keydown",kd);
    window.addEventListener("keyup",ku);
    return ()=>{window.removeEventListener("keydown",kd); window.removeEventListener("keyup",ku)}
  },[]);

  const deleteNode=useCallback((id:string)=>{
    const next:ConceptMapData={
      ...mapData,
      nodes:mapData.nodes.filter(n=>n.id!==id),
      edges:mapData.edges.filter(e=>e.from!==id&&e.to!==id)
    };
    setMapData(next);
    onChange?.(next);
    // Allow external sync again when user makes changes
    setIsManagingMapsInternally(false);
  },[mapData,onChange]);

  const deleteEdge=useCallback((edgeId:string)=>{
    const next:ConceptMapData={...mapData,edges:mapData.edges.filter(e=>e.id!==edgeId)};
    setMapData(next);
    onChange?.(next);
    // Allow external sync again when user makes changes
    setIsManagingMapsInternally(false);
  },[mapData,onChange]);

  useEffect(()=>{
    const onKeyDown=(e:KeyboardEvent)=>{
      const ae=document.activeElement as HTMLElement|null;
      const editing=ae&&(ae.isContentEditable||ae.tagName==='INPUT'||ae.tagName==='TEXTAREA');
      if((e.key==='Delete'||e.key==='Backspace')&&!editing){
        e.preventDefault();
        if(selectedId){deleteNode(selectedId); setSelectedId(null)}
        else if(selectedEdgeId){deleteEdge(selectedEdgeId); setSelectedEdgeId(null)}
      }
      if(e.key==='Escape'){
        setSelectedId(null); setSelectedEdgeId(null); setEditingId(null);
        setLinkMode(false); setLinkFromId(null); setCursorPos(null); setShowNodeMenu(null);
        setConnectionDragStartId(null);
      }
      if(e.key==='F2'&&selectedId&&!editing){
        e.preventDefault(); setEditingId(selectedId)
      }
    };
    window.addEventListener('keydown',onKeyDown);
    return ()=>window.removeEventListener('keydown',onKeyDown)
  },[selectedId,selectedEdgeId,deleteNode,deleteEdge]);

  const indexById=useMemo(()=>{
    const m=new Map<string,ConceptNode>();
    mapData.nodes.forEach(n=>m.set(n.id,n));
    return m
  },[mapData.nodes]);

  const findNodeAtPoint = useCallback((x: number, y: number) => {
    return mapData.nodes.find(node => {
      return x >= node.x && x <= node.x + DEFAULT_NODE_W && 
             y >= node.y && y <= node.y + DEFAULT_NODE_H;
    });
  }, [mapData.nodes]);

  const addEdge=useCallback((from:string,to:string,relationshipType:RelationType="generic",label?:string)=>{
    if(from===to) return;
    if(mapData.edges.some(e=>e.from===from&&e.to===to)) return;
    const next:ConceptMapData={
      ...mapData,
      edges:[...mapData.edges,{id:`e_${Date.now()}_${Math.random().toString(36).slice(2,6)}`,from,to,relationshipType,label}]
    };
    setMapData(next);
    onChange?.(next);
    // Allow external sync again when user makes changes
    setIsManagingMapsInternally(false);
  },[mapData,onChange]);

  const handleCreateEdgeWithRelationship = useCallback((fromId: string, toId: string, mousePos: Point) => {
    setShowRelationshipMenu({ x: mousePos.x, y: mousePos.y, fromId, toId });
  }, []);

  const confirmEdgeCreation = useCallback((relationshipType: RelationType) => {
    if (showRelationshipMenu) {
      addEdge(showRelationshipMenu.fromId, showRelationshipMenu.toId, relationshipType);
      setShowRelationshipMenu(null);
    }
  }, [showRelationshipMenu, addEdge]);

  const handleConnectionDragEnd = useCallback(() => {
    if (connectionDragStartId && cursorPos) {
      const targetNode = findNodeAtPoint(cursorPos.x, cursorPos.y);
      if (targetNode && targetNode.id !== connectionDragStartId) {
        handleCreateEdgeWithRelationship(connectionDragStartId, targetNode.id, cursorPos);
        setConnectionDragStartId(null);
        setLinkMode(false);
        setLinkFromId(null);
        setCursorPos(null);
        return;
      }
    }
    
    setConnectionDragStartId(null);
    setLinkMode(false);
    setLinkFromId(null);
    setCursorPos(null);
  }, [connectionDragStartId, cursorPos, findNodeAtPoint, handleCreateEdgeWithRelationship]);

  // Funzione per ottenere le coordinate corrette nel canvas
  const getCanvasCoords = useCallback((e: { clientX: number; clientY: number }) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }, []);

  const handleNodeMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      e.stopPropagation();
      setConnectionDragStartId(nodeId);
      setLinkMode(true);
      setLinkFromId(nodeId);
      
      setCursorPos(getCanvasCoords(e));
    } else {
      startDrag(e, indexById.get(nodeId)!);
    }
  }, [indexById, getCanvasCoords]);

  const startDrag=useCallback((e:React.MouseEvent,node:ConceptNode)=>{
    if(linkMode) return;
    e.preventDefault();
    e.stopPropagation();
    const mousePos = getCanvasCoords(e);
    const dragGroup=e.shiftKey;
    let sel=new Set<string>([node.id]);
    if(dragGroup){
      const adj=new Map<string,Set<string>>();
      mapData.nodes.forEach(n=>adj.set(n.id,new Set()));
      mapData.edges.forEach(ed=>{adj.get(ed.from)?.add(ed.to); adj.get(ed.to)?.add(ed.from)});
      sel=new Set<string>();
      const stack=[node.id];
      while(stack.length){
        const id=stack.pop()!;
        if(sel.has(id)) continue;
        sel.add(id);
        const neigh=adj.get(id)??[];
        if(neigh) neigh.forEach(nid=>{ if(!sel.has(nid)) stack.push(nid) })
      }
    }
    dragSelectionRef.current=sel;
    const positions=new Map<string,{x:number;y:number}>();
    mapData.nodes.forEach(n=>{ if(sel.has(n.id)) positions.set(n.id,{x:n.x,y:n.y}) });
    dragStartRef.current={mx:mousePos.x, my:mousePos.y, positions};
    dragOffset.current={dx:mousePos.x-node.x, dy:mousePos.y-node.y};
    setSelectedId(node.id);
    setDragId(node.id)
  },[linkMode,mapData.nodes,mapData.edges,getCanvasCoords]);

  const onMouseMove=useCallback((e:MouseEvent)=>{
    if(isPanning&&panStartRef.current){
      const s=panStartRef.current;
      const dx=e.clientX-s.x, dy=e.clientY-s.y;
      setPan({x:s.panX+dx,y:s.panY+dy})
    }
    if(dragId){
      const mousePos = getCanvasCoords(e);
      const st=dragStartRef.current;
      if(st&&dragSelectionRef.current.size>0){
        const dx=mousePos.x-st.mx, dy=mousePos.y-st.my;
        setMapData(prev=>({...prev,nodes:prev.nodes.map(n=>{
          if(!dragSelectionRef.current.has(n.id)) return n;
          const p=st.positions.get(n.id)!;
          return {...n,x:p.x+dx,y:p.y+dy}
        })}))
      } else {
        const {dx,dy}=dragOffset.current;
        setMapData(prev=>({...prev,nodes:prev.nodes.map(n=> n.id===dragId?{...n,x:mousePos.x-dx,y:mousePos.y-dy}:n)}))
      }
    }
    if((linkMode||connectionDragStartId)&&(linkFromId||connectionDragStartId)){
      setCursorPos(getCanvasCoords(e))
    }
  },[isPanning,dragId,linkMode,linkFromId,connectionDragStartId,getCanvasCoords]);

  const onMouseUp=useCallback(()=>{
    if(dragId){
      setDragId(null);
      dragSelectionRef.current.clear();
      dragStartRef.current=null;
      onChange?.(mapData)
    }
    
    if (connectionDragStartId) {
      handleConnectionDragEnd();
    }
  },[dragId,mapData,onChange,connectionDragStartId,handleConnectionDragEnd]);

  useEffect(()=>{
    const move=(e:MouseEvent)=>onMouseMove(e);
    const up=()=>onMouseUp();
    window.addEventListener('mousemove',move);
    window.addEventListener('mouseup',up);
    return ()=>{
      window.removeEventListener('mousemove',move);
      window.removeEventListener('mouseup',up)
    }
  },[onMouseMove,onMouseUp]);

  const addNodeAt=useCallback((x:number,y:number,label="Nuovo concetto")=>{
    const id=`n_${Date.now()}`;
    const next:ConceptMapData={...mapData,nodes:[...mapData.nodes,{id,label,x:x-DEFAULT_NODE_W/2,y:y-DEFAULT_NODE_H/2}]};
    setMapData(next);
    onChange?.(next);
    return id
  },[mapData,onChange]);

  const addConnectedNode=useCallback((fromId:string,dir:'top'|'right'|'bottom'|'left')=>{
    const from=mapData.nodes.find(n=>n.id===fromId);
    if(!from) return;
    let newX=from.x, newY=from.y;
    switch(dir){
      case 'top': newX=from.x; newY=from.y-DEFAULT_NODE_H-60; break;
      case 'right': newX=from.x+DEFAULT_NODE_W+60; newY=from.y; break;
      case 'bottom': newX=from.x; newY=from.y+DEFAULT_NODE_H+60; break;
      case 'left': newX=from.x-DEFAULT_NODE_W-60; newY=from.y; break
    }
    const newNodeId=`n_${Date.now()}`;
    const edgeId=`e_${Date.now()}_${Math.random().toString(36).slice(2,6)}`;
    const next:ConceptMapData={
      ...mapData,
      nodes:[...mapData.nodes,{id:newNodeId,label:"Nuovo concetto",x:newX,y:newY}],
      edges:[...mapData.edges,{id:edgeId,from:fromId,to:newNodeId}]
    };
    setMapData(next);
    onChange?.(next);
    setSelectedId(newNodeId);
    setEditingId(newNodeId)
  },[mapData,onChange]);

  const addNode=useCallback(()=>addNodeAt(100+Math.random()*400,100+Math.random()*300),[addNodeAt]);
  
  const handleCanvasRightClick=useCallback((e:React.MouseEvent)=>{
    e.preventDefault();
    setShowNodeMenu(getCanvasCoords(e))
  },[getCanvasCoords]);

  const handleCanvasDoubleClick=useCallback((e:React.MouseEvent)=>{
    const coords = getCanvasCoords(e);
    addNodeAt(coords.x, coords.y)
  },[addNodeAt, getCanvasCoords]);

  const buildContextText=useCallback(()=>{
    const adj=new Map<string,string[]>();
    mapData.nodes.forEach(n=>adj.set(n.id,[]));
    mapData.edges.forEach(e=>{
      const arr=adj.get(e.from);
      if(arr) arr.push(e.to)
    });
    let rootId=mapData.nodes[0]?.id??"";
    let max=-1;
    for(const [k,v] of adj.entries()){
      if(v.length>max){ max=v.length; rootId=k }
    }
    const idToLabel=new Map(mapData.nodes.map(n=>[n.id,n.label] as const));
    const lines:string[]=[];
    const visited=new Set<string>();
    function dfs(id:string,depth:number){
      if(visited.has(id)) return;
      visited.add(id);
      const label=idToLabel.get(id)??id;
      lines.push(`${"  ".repeat(depth)}- ${label}`);
      const children=adj.get(id)??[];
      for(const c of children) dfs(c,depth+1)
    }
    if(rootId) dfs(rootId,0);
    return (mapData.title?`# ${mapData.title}\n\n`:"")+lines.join("\n")
  },[mapData]);

  const copyContext=useCallback(async()=>{
    const text=buildContextText();
    try{
      await navigator.clipboard.writeText(text);
      onCopyContext?.(text)
    } catch {
      const ta=document.createElement('textarea');
      ta.value=text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      onCopyContext?.(text)
    }
  },[buildContextText,onCopyContext]);

  const toggleLinkMode=useCallback(()=>{
    setLinkMode(v=>{
      const next=!v;
      if(!next){ setLinkFromId(null); setCursorPos(null) }
      return next
    })
  },[]);

  const handleNodeClick=useCallback((e:React.MouseEvent,nodeId:string)=>{
    e.stopPropagation();
    if(editingId&&editingId!==nodeId) return;
    if(linkMode){
      if(!linkFromId) setLinkFromId(nodeId);
      else if(linkFromId===nodeId){ setLinkFromId(null); setCursorPos(null) }
      else { addEdge(linkFromId,nodeId); setLinkFromId(nodeId) }
    } else setSelectedId(nodeId)
  },[linkMode,linkFromId,addEdge,editingId]);

  const handleNodeDoubleClick=useCallback((e:React.MouseEvent,nodeId:string)=>{
    e.stopPropagation();
    setEditingId(nodeId);
    setSelectedId(nodeId)
  },[]);

  const handleConnectionClick=useCallback((e:React.MouseEvent,nodeId:string)=>{
    e.stopPropagation();
    if(!linkFromId){
      setLinkFromId(nodeId);
      setLinkMode(true)
    } else if(linkFromId===nodeId){
      setLinkFromId(null);
      setCursorPos(null)
    } else {
      addEdge(linkFromId,nodeId);
      setLinkFromId(nodeId)
    }
  },[linkFromId,addEdge]);

  const handleEdgeClick=useCallback((e:React.MouseEvent,edgeId:string)=>{
    e.stopPropagation();
    if(e.shiftKey){
      setMapData(prev=>{
        const nextEdges=prev.edges.map(ed=> 
          ed.id!==edgeId?ed:{...ed,curveSide:ed.curveSide===1?(-1 as const):ed.curveSide===-1?undefined:(1 as const)}
        );
        const next={...prev,edges:nextEdges};
        onChange?.(next);
        return next
      });
      return
    }
    setSelectedEdgeId(edgeId);
    setSelectedId(null)
  },[onChange]);

  const CANVAS_W=100000, CANVAS_H=100000;
  
  // Pre-render geometry
  const edgesRender = useMemo(()=>{
    const out: Array<{
      id: string;
      path: string;
      start: Point;
      end: Point;
      headAngleDeg: number;
      stroke: string;
      strokeWidth: number;
      mid: Point;
      relationshipType?: string;
      relationshipIcon?: string;
      relationshipLabel?: string;
    }> = [];
    for (const edge of mapData.edges){
      const fromNode = indexById.get(edge.from);
      const toNode   = indexById.get(edge.to);
      if(!fromNode || !toNode) continue;

      const { start, end, fromCenter, toCenter } = computeAnchors(fromNode, toNode);
      const side = (((edge.curveSide ?? determineCurveSide(fromNode, toNode)) as 1|-1) * (curveSignGlobal as 1|-1)) as 1|-1;

      let path = "";
      if (EDGE_STYLE === "curved"){
        const res = buildCurvedPathRadial(start, end, fromCenter, toCenter, side);
        path = res.path;
        var headDir = res.headDir;
      } else if (EDGE_STYLE === "orthogonal"){
        path = buildOrthogonalPath(start,end);
        headDir = { x: toCenter.x - end.x, y: toCenter.y - end.y };
      } else {
        path = buildStraightPath(start,end);
        headDir = { x: toCenter.x - end.x, y: toCenter.y - end.y };
      }

      const headAngleDeg = Math.atan2(headDir.y, headDir.x) * 180/Math.PI;

      const isSelected = selectedEdgeId === edge.id;
      const relationshipType = edge.relationshipType || "generic";
      const relationshipStyle = RELATIONSHIP_STYLES[relationshipType];

      out.push({
        id: edge.id,
        path,
        start, end,
        headAngleDeg,
        mid: pathMid(start,end),
        stroke: isSelected ? EDGE_SELECTED_COLOR : relationshipStyle.color,
        strokeWidth: isSelected ? 2.5 : 2,
        relationshipType,
        relationshipIcon: relationshipStyle.icon,
        relationshipLabel: relationshipStyle.label
      });
    }
    return out;
  },[mapData.edges, indexById, curveSignGlobal, selectedEdgeId]);

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      {/* Header Toolbar - Tutto a sinistra */}
      <div style={{
        display: 'flex',
        width: '100%',
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        padding: '12px 16px',
        minHeight: '60px',
        alignItems: 'center',
        gap: '16px',
        flexWrap: 'wrap'
      }}>
        {/* Titolo e data */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          {renamingMainTitle ? (
            <input
              type="text"
              value={tempMainTitle}
              onChange={(e) => setTempMainTitle(e.target.value)}
              onBlur={() => {
                const newTitle = tempMainTitle.trim() || 'Mappa Concettuale';
                const next = { ...mapData, title: newTitle };
                setMapData(next);
                onChange?.(next);
                setRenamingMainTitle(false);
                setIsManagingMapsInternally(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const newTitle = tempMainTitle.trim() || 'Mappa Concettuale';
                  const next = { ...mapData, title: newTitle };
                  setMapData(next);
                  onChange?.(next);
                  setRenamingMainTitle(false);
                  setIsManagingMapsInternally(false);
                } else if (e.key === 'Escape') {
                  setRenamingMainTitle(false);
                  setTempMainTitle('');
                }
              }}
              style={{
                fontSize: '18px',
                fontWeight: 'bold',
                color: '#333',
                backgroundColor: 'transparent',
                border: '1px solid #3b82f6',
                borderRadius: '4px',
                padding: '4px 8px'
              }}
              autoFocus
            />
          ) : (
            <h3 
              onClick={() => {
                setTempMainTitle(mapData.title || 'Mappa Concettuale');
                setRenamingMainTitle(true);
              }}
              style={{
                margin: 0,
                fontSize: '18px',
                fontWeight: 'bold',
                color: '#333',
                cursor: 'pointer'
              }}
              title="Clicca per rinominare"
            >
              {mapData.title || "Mappa Concettuale"}
            </h3>
          )}
          <span style={{fontSize: '14px', color: '#666'}}>
            📅 {new Date().toLocaleDateString('it-IT')}
          </span>
        </div>

        {/* Status indicators */}
        {lastSaveStatus === 'saving' && (
          <span style={{fontSize: '12px', color: '#3b82f6', display: 'flex', alignItems: 'center'}}>
            <div style={{width: '12px', height: '12px', border: '1px solid #3b82f6', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite', marginRight: '4px'}}></div>
            Salvando...
          </span>
        )}
        {lastSaveStatus === 'saved' && (
          <span style={{fontSize: '12px', color: '#16a34a'}}>✓ Salvato</span>
        )}
        {lastSaveStatus === 'error' && (
          <span style={{fontSize: '12px', color: '#dc2626'}}>⚠ Errore salvataggio</span>
        )}

        {/* Separatore che forza il layout corretto */}
        <div style={{width: '1px', height: '30px', backgroundColor: '#e5e7eb'}}></div>
        
        {/* Toolbar - Solo tasti essenziali */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap'
        }}>
          {/* Copy Context Button */}
          <button 
            onClick={copyContext} 
            style={{
              padding: '6px 10px',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: 'none',
              borderRadius: '6px',
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
            title="Copia contesto mappa negli appunti"
          >
            📋 Copia
          </button>
          
          {/* Historical Maps Button */}
          <button 
            onClick={() => setShowHistoricalMaps(!showHistoricalMaps)} 
            style={{
              padding: '6px 10px',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: 'none',
              borderRadius: '6px',
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
            title="Visualizza storico mappe concettuali"
          >
            📚 Storico
          </button>
          
        </div>
      </div>
      <div ref={containerRef} className="flex-1 overflow-hidden relative" 
        style={{cursor:isPanning?"grabbing":(spaceActive?"grab":connectionDragStartId?"crosshair":undefined)}}
        onMouseMove={(e)=>{
          if(!linkMode && !connectionDragStartId) return;
          setCursorPos(getCanvasCoords(e))
        }}
        onMouseDown={(e)=>{
          if(spaceActive||e.button===1){
            e.preventDefault();
            panStartRef.current={x:e.clientX,y:e.clientY,panX:pan.x,panY:pan.y};
            setIsPanning(true)
          }
        }}
        onClick={(e) => {
          // Close historical maps dropdown when clicking outside
          if (showHistoricalMaps && !(e.target as Element).closest('.absolute')) {
            setShowHistoricalMaps(false);
          }
        }}
        onMouseUp={()=>{ setIsPanning(false); panStartRef.current=null }}
        onMouseLeave={()=>{ setIsPanning(false); panStartRef.current=null }}
      >
        <div ref={canvasRef} className="relative" 
          style={{
            width:CANVAS_W,
            height:CANVAS_H,
            transform:`translate(${pan.x}px, ${pan.y}px)`,
            backgroundImage:"linear-gradient(#f3f4f6 1px, transparent 1px), linear-gradient(90deg, #f3f4f6 1px, transparent 1px)",
            backgroundSize:"24px 24px, 24px 24px",
            backgroundColor:"#ffffff"
          }}
          onDoubleClick={handleCanvasDoubleClick}
          onContextMenu={handleCanvasRightClick}
          onClick={()=>{
            if(editingId) return;
            setSelectedId(null);
            setSelectedEdgeId(null);
            setShowNodeMenu(null)
          }}
          title="Doppio click per creare un nuovo nodo qui, tasto destro per menu"
          onMouseDown={(e)=>{
            if((e.button===0)&&!linkMode&&!editingId){
              const now = Date.now();
              if (now - lastClickTimeRef.current < 300) {
                // È un doppio click, non avviare il panning
                lastClickTimeRef.current = 0;
                return;
              }
              lastClickTimeRef.current = now;
              
              e.preventDefault();
              e.stopPropagation();
              panStartRef.current={x:e.clientX,y:e.clientY,panX:pan.x,panY:pan.y};
              setIsPanning(true)
            }
          }}
        >
          {/* 1) LINEE (sotto i nodi) */}
          <svg
            width={CANVAS_W}
            height={CANVAS_H}
            className="absolute left-0 top-0"
            style={{ pointerEvents: "auto", zIndex: 5, overflow: "visible" }}
          >
            {edgesRender.map(er=>(
              <g key={er.id}>
                <path 
                  d={er.path} 
                  stroke="transparent" 
                  strokeWidth={EDGE_HIT_WIDTH} 
                  fill="none" 
                  style={{cursor:"pointer",pointerEvents:"stroke"}} 
                  onClick={(evt)=>handleEdgeClick(evt as any, er.id)} 
                />
                <path 
                  d={er.path} 
                  stroke={er.stroke} 
                  strokeWidth={er.strokeWidth} 
                  fill="none"
                  vectorEffect="non-scaling-stroke"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ pointerEvents: "none" }}
                />
                
                {selectedEdgeId===er.id && (
                  <circle cx={er.mid.x} cy={er.mid.y} r={5} fill={EDGE_SELECTED_COLOR} stroke="white" strokeWidth={2} />
                )}
                {/* Icona del tipo di relazione */}
                <circle cx={er.mid.x} cy={er.mid.y} r={8} fill="white" stroke={er.stroke} strokeWidth={1.5} />
                <text 
                  x={er.mid.x} 
                  y={er.mid.y + 2} 
                  textAnchor="middle" 
                  fontSize="10" 
                  fill={er.stroke}
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {(er as any).relationshipIcon}
                </text>
              </g>
            ))}
            
            {/* Rubber-band durante il collegamento */}
            {(()=>{
              if(!((linkMode||connectionDragStartId)&&(linkFromId||connectionDragStartId)&&cursorPos)) return null;
              const sourceId = linkFromId || connectionDragStartId;
              const fromNode = sourceId ? indexById.get(sourceId) : null;
              if(!fromNode) return null;
              // Calcola il punto di partenza direttamente dal centro del nodo al cursore
              const fromCenter = centerOfNode(fromNode);
              const direction = {
                x: cursorPos.x - fromCenter.x,
                y: cursorPos.y - fromCenter.y
              };
              const distance = Math.hypot(direction.x, direction.y);
              
              // Normalizza la direzione
              const dirNormalized = distance > 0 ? {
                x: direction.x / distance,
                y: direction.y / distance
              } : { x: 0, y: 0 };
              // Calcola il punto di partenza sul bordo del nodo
              const start = {
                x: fromCenter.x + dirNormalized.x * (DEFAULT_NODE_W / 2),
                y: fromCenter.y + dirNormalized.y * (DEFAULT_NODE_H / 2)
              };
              // Crea una linea retta dal bordo del nodo al cursore
              const path = `M ${start.x} ${start.y} L ${cursorPos.x} ${cursorPos.y}`;
              return (
                <path 
                  d={path} 
                  stroke="#94a3b8" 
                  strokeWidth={2} 
                  fill="none" 
                  strokeDasharray="6 4" 
                  strokeLinecap="round" 
                  style={{pointerEvents:"none"}}
                />
              );
            })()}
          </svg>

          {/* 2) NODI (sopra le linee) */}
          {mapData.nodes.map(n=> (
            <div key={n.id} 
              className={`absolute rounded-2xl shadow-md bg-white select-none group ${
                selectedId===n.id?"border-2 border-blue-400 ring-2 ring-blue-200":"border border-gray-200"
              }`} 
              style={{
                left: n.x, 
                top: n.y, 
                minWidth: MIN_NODE_W,
                maxWidth: MAX_NODE_W,
                minHeight: MIN_NODE_H,
                width: 'fit-content',
                height: 'fit-content',
                zIndex: 10
              }}
            >
              <div className="w-full h-full p-3 cursor-move rounded-2xl" 
                onMouseDown={(e)=>handleNodeMouseDown(e,n.id)} 
                onClick={(e)=>handleNodeClick(e,n.id)} 
                onDoubleClick={(e)=>{e.stopPropagation(); setEditingId(n.id); setSelectedId(n.id)}} 
                title="Click per selezionare, doppio click per rinominare, drag per spostare (Shift+drag per gruppo, Ctrl+drag per collegare)"
              >
                {editingId===n.id? (
                  <textarea 
                    defaultValue={n.label} 
                    className="text-xs font-semibold text-gray-700 w-full bg-transparent border-none outline-none ring-1 ring-blue-300 rounded px-1 resize-none leading-tight" 
                    autoFocus
                    rows={1}
                    style={{ minHeight: '1.2em' }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = 'auto';
                      target.style.height = target.scrollHeight + 'px';
                    }} 
                    onClick={(e)=>e.stopPropagation()} 
                    onMouseDown={(e)=>e.stopPropagation()} 
                    onBlur={(e)=>{
                      setTimeout(()=>{
                        const textarea=e.target as HTMLTextAreaElement;
                        const newLabel=textarea.value.trim()||n.label;
                        const next={...mapData,nodes:mapData.nodes.map(x=>x.id===n.id?{...x,label:newLabel}:x)};
                        setMapData(next);
                        onChange?.(next);
                        setEditingId(null)
                      },100)
                    }} 
                    onKeyDown={(e)=>{
                      if(e.key==='Enter' && !e.shiftKey){
                        e.preventDefault();
                        const newLabel=(e.currentTarget as HTMLTextAreaElement).value.trim()||n.label;
                        const next={...mapData,nodes:mapData.nodes.map(x=>x.id===n.id?{...x,label:newLabel}:x)};
                        setMapData(next);
                        onChange?.(next);
                        setEditingId(null)
                      } else if(e.key==='Escape'){
                        setEditingId(null)
                      }
                    }} 
                  />
                ) : (
                  <div className="text-xs font-semibold text-gray-700 break-words leading-tight">
                    {n.label}
                  </div>
                )}
                <div className="mt-1 text-[11px] text-gray-500">ID: <span className="font-mono">{n.id}</span></div>
              </div>
              {selectedId===n.id && (
                <>
                  <button className="absolute -top-3 left-1/2 transform -translate-x-1/2 w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold hover:bg-green-600 transition-colors border-2 border-white shadow-md" 
                    style={{zIndex:20}} 
                    onClick={(e)=>{e.stopPropagation(); addConnectedNode(n.id,'top')}} 
                    title="Crea nuovo nodo collegato sopra"
                  >+</button>
                  <button className="absolute -right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold hover:bg-green-600 transition-colors border-2 border-white shadow-md" 
                    style={{zIndex:20}} 
                    onClick={(e)=>{e.stopPropagation(); addConnectedNode(n.id,'right')}} 
                    title="Crea nuovo nodo collegato a destra"
                  >+</button>
                  <button className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold hover:bg-green-600 transition-colors border-2 border-white shadow-md" 
                    style={{zIndex:20}} 
                    onClick={(e)=>{e.stopPropagation(); addConnectedNode(n.id,'bottom')}} 
                    title="Crea nuovo nodo collegato sotto"
                  >+</button>
                  <button className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold hover:bg-green-600 transition-colors border-2 border-white shadow-md" 
                    style={{zIndex:20}} 
                    onClick={(e)=>{e.stopPropagation(); addConnectedNode(n.id,'left')}} 
                    title="Crea nuovo nodo collegato a sinistra"
                  >+</button>
                </>
              )}
              {linkMode && (
                <>
                  <div className={`absolute -top-2 left-1/2 transform -translate-x-1/2 w-4 h-4 rounded-full border-2 cursor-crosshair ${
                    linkFromId===n.id?"bg-blue-500 border-blue-600":"bg-white border-blue-400"
                  } hover:bg-blue-100 transition-colors`} 
                    style={{zIndex:20}} 
                    onClick={(e)=>handleConnectionClick(e,n.id)} 
                    title="Click per iniziare/terminare collegamento" 
                  />
                  <div className={`absolute -right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 rounded-full border-2 cursor-crosshair ${
                    linkFromId===n.id?"bg-blue-500 border-blue-600":"bg-white border-blue-400"
                  } hover:bg-blue-100 transition-colors`} 
                    style={{zIndex:20}} 
                    onClick={(e)=>handleConnectionClick(e,n.id)} 
                    title="Click per iniziare/terminare collegamento" 
                  />
                  <div className={`absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-4 h-4 rounded-full border-2 cursor-crosshair ${
                    linkFromId===n.id?"bg-blue-500 border-blue-600":"bg-white border-blue-400"
                  } hover:bg-blue-100 transition-colors`} 
                    style={{zIndex:20}} 
                    onClick={(e)=>handleConnectionClick(e,n.id)} 
                    title="Click per iniziare/terminare collegamento" 
                  />
                  <div className={`absolute -left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 rounded-full border-2 cursor-crosshair ${
                    linkFromId===n.id?"bg-blue-500 border-blue-600":"bg-white border-blue-400"
                  } hover:bg-blue-100 transition-colors`} 
                    style={{zIndex:20}} 
                    onClick={(e)=>handleConnectionClick(e,n.id)} 
                    title="Click per iniziare/terminare collegamento" 
                  />
                </>
              )}
            </div>
          ))}

          {/* 3) PUNTE (sopra le nodes, pointer-events: none) */}
          <svg
            width={CANVAS_W}
            height={CANVAS_H}
            className="absolute left-0 top-0"
            style={{ pointerEvents: "none", zIndex: 30, overflow: "visible" }}
          >
            {edgesRender.map(er=>(
              <g key={er.id} transform={`translate(${er.end.x}, ${er.end.y}) rotate(${er.headAngleDeg})`}>
                <path d={`M 0 0 L ${-HEAD_LEN} ${HEAD_HALF} L ${-HEAD_LEN} ${-HEAD_HALF} Z`} fill={er.stroke} />
              </g>
            ))}
          </svg>

          {showNodeMenu && (
            <div className="absolute bg-white border border-gray-300 rounded-lg shadow-lg py-2 z-20" 
              style={{left:showNodeMenu.x, top:showNodeMenu.y}}
            >
              <button className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" 
                onClick={()=>{addNodeAt(showNodeMenu.x!,showNodeMenu.y!); setShowNodeMenu(null)}}
              >🟢 Nuovo nodo</button>
              <button className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" 
                onClick={()=>{addNodeAt(showNodeMenu.x!,showNodeMenu.y!,"Concetto importante"); setShowNodeMenu(null)}}
              >⭐ Concetto importante</button>
              <button className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100" 
                onClick={()=>{addNodeAt(showNodeMenu.x!,showNodeMenu.y!,"Domanda"); setShowNodeMenu(null)}}
              >❓ Domanda</button>
            </div>
          )}

          {/* Menu selezione tipo di relazione */}
          {showRelationshipMenu && (
            <div className="absolute bg-white border border-gray-300 rounded-lg shadow-lg py-2 z-30 max-h-96 overflow-y-auto" 
              style={{left:showRelationshipMenu.x, top:showRelationshipMenu.y, width: "280px"}}
            >
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 border-b">
                Seleziona tipo di relazione
              </div>
              {Object.entries(RELATIONSHIP_STYLES).map(([type, style]) => (
                <button
                  key={type}
                  className="flex items-center w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                  onClick={() => confirmEdgeCreation(type as RelationType)}
                >
                  <span className="text-lg mr-3" style={{ color: style.color }}>
                    {style.icon}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{style.label}</div>
                    <div className="text-xs text-gray-500">{style.description}</div>
                  </div>
                </button>
              ))}
              <div className="border-t pt-2">
                <button
                  className="block w-full text-left px-4 py-2 text-sm text-gray-500 hover:bg-gray-100"
                  onClick={() => setShowRelationshipMenu(null)}
                >
                  ❌ Annulla
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Historical Maps Dropdown */}
      {showHistoricalMaps && (
        <div className="absolute top-16 right-4 bg-white border border-gray-300 rounded-lg shadow-lg z-30 w-80 max-h-96 overflow-y-auto">
          <div className="px-4 py-3 border-b bg-gray-50">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">📚 Storico Mappe</h3>
              <button
                onClick={() => setShowHistoricalMaps(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
          </div>
          
          <div className="p-2">
            {conceptMaps.length === 0 ? (
              <div className="px-4 py-6 text-center text-gray-500">
                <p>Nessuna mappa salvata</p>
                <button
                  onClick={createNewMap}
                  className="mt-2 text-blue-600 hover:text-blue-800 text-sm"
                >
                  Crea la tua prima mappa
                </button>
              </div>
            ) : (
              <>
                <div className="mb-3">
                  <button
                    onClick={createNewMap}
                    className="w-full px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
                  >
                    + Nuova Mappa
                  </button>
                </div>
                
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {conceptMaps
                    .sort((a, b) => new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime())
                    .map(map => (
                    <div
                      key={map.id}
                      className={`flex items-center justify-between p-2 rounded hover:bg-gray-100 ${
                        currentMapId === map.id ? 'bg-blue-50 border border-blue-200' : ''
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        {renamingMapId === map.id ? (
                          <input
                            type="text"
                            value={tempTitle}
                            onChange={(e) => setTempTitle(e.target.value)}
                            onBlur={() => confirmRename(map.id!)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') confirmRename(map.id!);
                              if (e.key === 'Escape') cancelRename();
                            }}
                            className="w-full px-2 py-1 text-sm border border-blue-300 rounded"
                            autoFocus
                          />
                        ) : (
                          <button
                            onClick={() => loadHistoricalMap(map.id!, {
                              title: map.title || 'Mappa Senza Titolo',
                              nodes: map.nodes || [],
                              edges: map.edges || []
                            })}
                            className="w-full text-left"
                          >
                            <div className="font-medium text-sm truncate">
                              {map.title || 'Mappa Senza Titolo'}
                            </div>
                            <div className="text-xs text-gray-500">
                              {map.nodes?.length || 0} nodi • {map.edges?.length || 0} collegamenti
                            </div>
                            <div className="text-xs text-gray-400">
                              {new Date(map.updatedAt || 0).toLocaleString()}
                            </div>
                          </button>
                        )}
                      </div>
                      
                      <div className="flex items-center space-x-1 ml-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startRenaming(map.id!, map.title || 'Mappa Senza Titolo');
                          }}
                          className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-100 rounded"
                          title="Rinomina"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSingleMap(map.id!, map.title || 'Mappa Senza Titolo');
                          }}
                          className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-100 rounded"
                          title="Elimina"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">⚠️</span>
              <h3 className="text-lg font-semibold text-gray-900">
                Conferma Eliminazione
              </h3>
            </div>
            
            <div className="mb-6 text-gray-600">
              {showDeleteConfirm.type === 'single' && (
                <p>
                  Sei sicuro di voler eliminare la mappa <strong>"{showDeleteConfirm.mapTitle}"</strong>?
                  <br />
                  <span className="text-sm text-red-600 mt-2 block">Questa azione è irreversibile.</span>
                </p>
              )}
              {showDeleteConfirm.type === 'multiple' && (
                <p>
                  Sei sicuro di voler eliminare <strong>{selectedMapsForDeletion.size} mappe selezionate</strong>?
                  <br />
                  <span className="text-sm text-red-600 mt-2 block">Questa azione è irreversibile.</span>
                </p>
              )}
              {showDeleteConfirm.type === 'all' && (
                <p>
                  Sei sicuro di voler eliminare <strong>tutte le {conceptMaps.length} mappe</strong>?
                  <br />
                  <span className="text-sm text-red-600 mt-2 block">Questa azione è irreversibile e cancellerà tutti i tuoi dati!</span>
                </p>
              )}
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-50"
              >
                Annulla
              </button>
              <button
                onClick={confirmDeletion}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg disabled:opacity-50 flex items-center"
              >
                {isDeleting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Eliminando...
                  </>
                ) : (
                  <>🗑️ Elimina</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
