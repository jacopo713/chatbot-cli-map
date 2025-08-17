"use client";

import React, { useState, useMemo, useCallback } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { prism } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import PreviewModal from './PreviewModal';

interface CodeBlockProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
  onInteraction?: (filePath: string, content: string, language: string, isAutoCapture: boolean) => void;
  isAutoCaptureEnabled?: boolean;
  hasActiveProject?: boolean;
  projectFiles?: Array<{ path: string; content: string; language: string }>;
  [key: string]: any;
}

type PathCandidate = { path: string; score: number; source: string };

const pickBestCandidate = (candidates: PathCandidate[]): string | null => {
  if (!candidates.length) return null;
  // Ordina per punteggio discendente; in caso di parità, preferisci path più specifici (più segmenti)
  const sorted = candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    const aDepth = a.path.split('/').length;
    const bDepth = b.path.split('/').length;
    return bDepth - aDepth;
  });
  return sorted[0].path;
};

// Helper: rilevamento percorso file dal contenuto
const detectFilePathFromContent = (code: string, language: string): string | null => {
  // TypeScript/JavaScript/React
  if (['typescript', 'javascript', 'tsx', 'jsx', 'ts', 'js'].includes(language)) {
      // Heuristica: classica utility "cn" con clsx + tailwind-merge -> lib/utils.ts
      const looksLikeCnUtil = /export\s+function\s+cn\s*\(/.test(code)
        && /clsx/.test(code)
        && /tailwind-merge/.test(code);
      if (looksLikeCnUtil) {
        return 'lib/utils.ts';
      }

    const componentMatch = code.match(/export\s+(?:default\s+)?(?:function|const)\s+(\w+)/);
    if (componentMatch) {
      const componentName = componentMatch[1];

      // App Router / Pages Router special cases
      const extDetected = language.includes('tsx') || language.includes('jsx') ? 'tsx' : 'ts';
      const nameLc = componentName.toLowerCase();

      // Home-like components -> app router page
      if (['home', 'homepage', 'index', 'page'].includes(nameLc)) {
        return `src/app/page.${extDetected}`;
      }

      // layout -> app router layout
      if (nameLc === 'layout') {
        return `src/app/layout.${extDetected}`;
      }

      // App component -> pages router _app
      if (nameLc === 'app') {
        return `src/pages/_app.${extDetected}`;
      }

      if (componentName === 'Greeting' || componentName === 'Hello') {
        const extDetected2 = language.includes('tsx') || language.includes('jsx') ? 'tsx' : 'ts';
        return `src/components/${componentName}.${extDetected2}`;
      }

      const extDetected3 = language.includes('tsx') || language.includes('jsx') ? 'tsx' : 'ts';
      return `src/components/${componentName}.${extDetected3}`;
    }

    if (code.includes('export interface') || code.includes('export type')) {
      const typeMatch = code.match(/export\s+(?:interface|type)\s+(\w+)/);
      if (typeMatch) {
        const typeName = typeMatch[1];
        if (typeName.includes('API') || typeName.includes('Response') || typeName.includes('Request')) {
          return 'src/types/api.ts';
        }
        return `src/types/${typeName.toLowerCase()}.ts`;
      }
    }

    if (code.includes('NextConfig') || code.includes('next/config')) {
      return 'next.config.js';
    }

    if (code.includes('NextRequest') || code.includes('NextResponse')) {
      return 'src/app/api/route.ts';
    }
  }

  // Python
  if (language === 'python' || language === 'py') {
    if (code.includes('FastAPI') || code.includes('app = FastAPI')) {
      return 'backend/main.py';
    }
    if (code.includes('from fastapi')) {
      const routerMatch = code.match(/router\s*=\s*APIRouter/);
      if (routerMatch) {
        return 'backend/routers/api.py';
      }
    }
    const classMatch = code.match(/class\s+(\w+)/);
    if (classMatch) {
      return `backend/${classMatch[1].toLowerCase()}.py`;
    }
  }

  // JSON
  if (language === 'json') {
    if (code.includes('"compilerOptions"')) {
      return 'tsconfig.json';
    }
    if (code.includes('"name"') && code.includes('"version"')) {
      return 'package.json';
    }
  }

  // .env
  if (language === 'bash' || language === 'shell' || language === 'env' || language === '') {
    if (code.includes('=') && (
      code.includes('API_KEY') ||
      code.includes('DATABASE_URL') ||
      code.includes('SECRET') ||
      code.includes('TOKEN') ||
      code.includes('PORT') ||
      code.includes('NODE_ENV')
    )) {
      return '.env.local';
    }
  }

  // CSS
  if (language === 'css' || language === 'scss' || language === 'sass') {
    if (code.includes(':root') || code.includes('body')) {
      return 'src/app/globals.css';
    }
    return 'src/styles/styles.css';
  }

  // HTML
  if (language === 'html') {
    if (code.includes('<!DOCTYPE') || code.includes('<html')) {
      return 'public/index.html';
    }
  }

  return null;
};

// Pulisci eventuali menzioni di path all'inizio del blocco
const cleanCodeFromPathMentions = (code: string): { cleanCode: string; mentionedPath: string | null } => {
  const pathMentionPatterns = [
    /^`([^`]+\.[a-z]+)`[\s\n]*/i,
    /^([a-zA-Z0-9/_.-]+\.[a-z]+)[\s\n]*/i,
    /^(?:in\s+|file\s+)?`?([a-zA-Z0-9/_.-]+\.[a-z]+)`?[\s\n]*/i,
  ];

  for (const pattern of pathMentionPatterns) {
    const match = code.match(pattern);
    if (match) {
      const possiblePath = match[1];
      const extensionMatch = possiblePath.match(/\.(tsx?|jsx?|py|css|html|json|env|local|md|yml|yaml|sh|bash)$/i);

      if (extensionMatch) {
        const cleanedCode = code.replace(pattern, '').trim();
        if (cleanedCode.length > 0 && !cleanedCode.startsWith('.')) {
          return { cleanCode: cleanedCode, mentionedPath: possiblePath };
        }
      }
    }
  }

  return { cleanCode: code, mentionedPath: null };
};

// È solo un file path con estensione
const isJustFilePath = (text: string): boolean => {
  const trimmed = text.trim();
  const filePathPattern = /^[a-zA-Z0-9/_.-]+\.(tsx?|jsx?|py|css|html|json|env|local|md|yml|yaml|sh|bash)$/;
  return filePathPattern.test(trimmed) && !trimmed.includes('\n') && trimmed.length < 200;
};

// È un path-like (alias o directory) SENZA estensione, da evidenziare come chip inline
const isPathLikeToken = (text: string): boolean => {
  const trimmed = text.trim();
  if (!trimmed || trimmed.length > 200) return false;
  if (trimmed.includes('\n')) return false;
  if (/\s/.test(trimmed)) return false; // niente spazi
  if (trimmed.includes('://')) return false; // evita URL
  // Evita nomi npm scoped tipo @tanstack/... (accettiamo solo alias @/ )
  if (trimmed.startsWith('@') && !trimmed.startsWith('@/')) return false;

  const startsWithKnownAliasOrDir = [
    '@/', '~/', './', '../',
    'src/', 'app/', 'pages/', 'components/', 'lib/', 'public/',
    'styles/', 'server/', 'backend/', 'frontend/', 'config/',
    'scripts/', 'bin/', 'test/', 'tests/', '__tests__/', 'api/', 'utils/', 'assets/'
  ].some(prefix => trimmed.startsWith(prefix));

  if (!startsWithKnownAliasOrDir) return false;

  // Caratteri ammessi nei path di progetto
  return /^[A-Za-z0-9_\-./[```]+\/?$/.test(trimmed);
};

// È un "nome di pacchetto/estensione" stile parola Capitalizzata (ESLint, Prettier, TypeScript)
const isPackageName = (text: string): boolean => {
  const trimmed = text.trim();

  if (trimmed.startsWith('npm ') ||
      trimmed.startsWith('npx ') ||
      trimmed.startsWith('yarn ') ||
      trimmed.startsWith('pnpm ') ||
      trimmed.startsWith('cd ') ||
      trimmed.startsWith('mkdir ') ||
      trimmed.includes(' ')) {
    return false;
  }

  if (trimmed.includes('/')) return false;

  if (trimmed.includes('.') ||
      trimmed.includes('=') ||
      trimmed.includes('{') ||
      trimmed.includes(';') ||
      trimmed.includes(':') ||
      trimmed.includes('(') ||
      trimmed.includes(')') ||
      trimmed.includes('@')) {
    return false;
  }

  const packagePattern = /^[A-Z][A-Za-z0-9\-_]*$/;
  return packagePattern.test(trimmed) &&
         trimmed.length > 2 &&
         trimmed.length < 50;
};

const CodeBlock = React.memo(({ 
  node, 
  inline, 
  className, 
  children, 
  onInteraction,
  isAutoCaptureEnabled = false,
  hasActiveProject = false,
  ...props 
}: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  const [autoSaved, setAutoSaved] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [isPathPickerOpen, setIsPathPickerOpen] = useState(false);
  const [tempPath, setTempPath] = useState('');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const extractTextFromChildren = useCallback((children: React.ReactNode): string => {
    if (!children) return '';
    if (typeof children === 'string') return children;
    if (typeof children === 'number') return children.toString();
    if (Array.isArray(children)) {
      return children.map(extractTextFromChildren).join('');
    }
    if (React.isValidElement(children)) {
      const el = children as React.ReactElement<any>;
      return extractTextFromChildren(el.props?.children);
    }
    return String(children);
  }, []);

  const { filePath, cleanCode, language, isFileCandidate, isPathOnly, isPackageNameType, confidence, candidates } = useMemo(() => {
    try {
      const rawCode = node?.value || extractTextFromChildren(children);
      let code = (rawCode || '').replace(/\n$/, '');

      // Linguaggio dalla classe
      const languageMatch = className?.match(/language-([\w-]+)/);
      const detectedLanguage = languageMatch ? languageMatch[1] : '';

      // Percorso "chip" (file con estensione o path-like alias/dir)
      const pathOnly = isJustFilePath(code) || isPathLikeToken(code);

      // Nome pacchetto tipo ESLint/Prettier
      const packageNameType = isPackageName(code);

      if (packageNameType) {
        return {
          filePath: null,
          cleanCode: code,
          language: 'text',
          isFileCandidate: false,
          isPathOnly: false,
          isPackageNameType: true
        };
      }

      // Se è un path/path-like singolo, mostrato come chip evidenziato (inline)
      if (pathOnly) {
        return {
          filePath: null,
          cleanCode: code,
          language: 'text',
          isFileCandidate: false,
          isPathOnly: true,
          isPackageNameType: false
        };
      }

      // Per inline standard
      if (inline) {
        return {
          filePath: null,
          cleanCode: code,
          language: detectedLanguage || 'text',
          isFileCandidate: false,
          isPathOnly: false,
          isPackageNameType: false
        };
      }

      // Pulisci eventuali menzioni esplicite di path in testa
      const { cleanCode: cleanedFromMentions, mentionedPath } = cleanCodeFromPathMentions(code);
      code = cleanedFromMentions;

      // Determina se è un candidato "file"
      const lineCount = code.split('\n').length;
      const hasCodeStructure = /(?:function|class|export|import|def|return|const|let|var)\s/.test(code);
      const isCommand = ['bash', 'shell', 'sh'].includes(detectedLanguage);
      const isPlainText = detectedLanguage === 'text' || detectedLanguage === '';
      const isConfig = ['json', 'yaml', 'yml'].includes(detectedLanguage);
      const isEnvFile = code.includes('=') && (code.includes('_KEY') || code.includes('_URL') || code.includes('_SECRET'));

      const isFileCandidate = (!isCommand || isEnvFile) && !isPlainText && (lineCount > 2 || hasCodeStructure || isConfig || isEnvFile);

      // Rileva eventuali path espliciti nell'intestazione del blocco (priorità assoluta)
      const filePathPatterns = [
        /^\/\/ @file-path (.+)\n/,
        /^\/\/ (.+\.(tsx?|jsx?|py|css|html|json|md|yml|yaml))\n/,
        /^# (.+\.(py|sh|bash|rb))\n/,
        /^<!-- (.+\.(html|xml|svg)) -->\n/,
      ];

      let existingPath: string | null = null;
      let cleanedCode = code;

      for (const pattern of filePathPatterns) {
        const match = code.match(pattern);
        if (match) {
          existingPath = match[1];
          cleanedCode = code.replace(pattern, '');
          break;
        }
      }

      // Se c'è una menzione esplicita o un header con filename, usala e salta lo scoring
      if (existingPath || mentionedPath) {
        existingPath = existingPath || mentionedPath || null;
        return {
          filePath: existingPath,
          cleanCode: cleanedCode,
          language: detectedLanguage || 'text',
          isFileCandidate,
          isPathOnly: false,
          isPackageNameType: false,
          confidence: 100,
          candidates: existingPath ? [{ path: existingPath, score: 100, source: 'explicit' }] : []
        };
      }

      // Resolver a punteggio: colleziona candidati e scegli il migliore
      let candidateList: PathCandidate[] = [];
      if (!existingPath && isFileCandidate && isAutoCaptureEnabled) {
        const localCandidates: PathCandidate[] = [];

        // Candidate da contenuto
        const contentGuess = detectFilePathFromContent(cleanedCode, detectedLanguage);
        if (contentGuess) localCandidates.push({ path: contentGuess, score: 35, source: 'content-heuristic' });

        // Env file forte
        if (isEnvFile) localCandidates.push({ path: '.env.local', score: 50, source: 'env' });

        // Heuristica generica per componenti se export + React
        if (/export\s+(?:default\s+)?(?:function|const)\s+/.test(cleanedCode) && /react/i.test(cleanedCode)) {
          localCandidates.push({ path: 'src/components/Component.tsx', score: 15, source: 'heuristic' });
        }

        // Applica preferenze utente (se presenti) come boost
        try {
          if (typeof window !== 'undefined') {
            const raw = window.localStorage.getItem('path-preferences');
            if (raw) {
              const prefs = JSON.parse(raw) as Record<string, string>;
              localCandidates.forEach(c => {
                const preferredDir = prefs[c.source];
                if (preferredDir && c.path.startsWith(preferredDir)) {
                  c.score += 20;
                }
              });
            }
          }
        } catch {}

        candidateList = localCandidates;
        existingPath = pickBestCandidate(localCandidates);
      }

      if (!existingPath && isEnvFile) {
        existingPath = '.env.local';
      }

      return {
        filePath: existingPath,
        cleanCode: cleanedCode,
        language: detectedLanguage || 'text',
        isFileCandidate,
        isPathOnly: false,
        isPackageNameType: false,
        confidence: (candidateList && candidateList.length) ? Math.max(...candidateList.map(c => c.score)) : (existingPath ? 50 : 0),
        candidates: candidateList
      };
    } catch (error) {
      console.error('Error processing code block:', error);
      return {
        filePath: null,
        cleanCode: String(children ?? ''),
        language: 'text',
        isFileCandidate: false,
        isPathOnly: false,
        isPackageNameType: false,
        confidence: 0,
        candidates: []
      };
    }
  }, [node, children, className, extractTextFromChildren, inline, isAutoCaptureEnabled]);

  // Ambiguità: bassa confidenza o candidati con punteggi vicini
  const shouldDisambiguate = useMemo(() => {
    if (!isFileCandidate || !isAutoCaptureEnabled) return false;
    if (!filePath) return true;
    const lowConfidence = (confidence || 0) < 30;
    const closeScores = (candidates || []).length > 1 && (() => {
      const sorted = [...(candidates || [])].sort((a,b)=>b.score-a.score);
      return sorted[0].score - sorted[1].score <= 10;
    })();
    return lowConfidence || closeScores;
  }, [isFileCandidate, isAutoCaptureEnabled, filePath, confidence, candidates]);

  const openPathPicker = useCallback(() => {
    const suggested = filePath || ((candidates && candidates[0]) ? candidates[0].path : '');
    setTempPath(suggested);
    setIsPathPickerOpen(true);
  }, [filePath, candidates]);

  const saveWithPath = useCallback((finalPath: string, isAuto: boolean) => {
    if (!onInteraction || !isFileCandidate) return;
    const finalCode = finalPath.endsWith('.env') || finalPath.endsWith('.env.local') 
      ? cleanCode
      : `// @file-path ${finalPath}\n${cleanCode}`;

    // Salva preferenza se la scelta corregge un fallback generico
    try {
      if (typeof window !== 'undefined' && candidates && candidates.length > 0) {
        const top = [...candidates].sort((a,b)=>b.score-a.score)[0];
        const chosenDir = finalPath.includes('/') ? finalPath.split('/').slice(0, -1).join('/') + '/' : '';
        if (top && chosenDir && top.source === 'heuristic') {
          const raw = window.localStorage.getItem('path-preferences');
          const prefs = raw ? JSON.parse(raw) : {};
          prefs[top.source] = chosenDir;
          window.localStorage.setItem('path-preferences', JSON.stringify(prefs));
        }
      }
    } catch {}

    onInteraction(finalPath, finalCode, language, isAuto);
    setIsPathPickerOpen(false);
    setAutoSaved(true);
    setTimeout(() => setAutoSaved(false), 2000);
  }, [onInteraction, isFileCandidate, cleanCode, language, candidates]);

  const handleClick = useCallback(() => {
    if (isAutoCaptureEnabled && isFileCandidate) {
      if (shouldDisambiguate || !filePath) {
        openPathPicker();
        return;
      }
      // salvataggio diretto
      saveWithPath(filePath, true);
    }
  }, [isAutoCaptureEnabled, isFileCandidate, shouldDisambiguate, filePath, openPathPicker, saveWithPath]);

  const handleCopy = useCallback(async () => {
    try {
      if (isFileCandidate && (shouldDisambiguate || !filePath)) {
        openPathPicker();
        return;
      }
      const finalCode = filePath && !filePath.endsWith('.env') && !filePath.endsWith('.env.local')
        ? `// @file-path ${filePath}\n${cleanCode}`
        : cleanCode;

      await navigator.clipboard.writeText(finalCode);
      setCopied(true);

      if (onInteraction && filePath && isFileCandidate) {
        onInteraction(filePath, finalCode, language, false);
      }

      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Errore durante la copia:', err);
      setCopied(false);
    }
  }, [filePath, cleanCode, language, onInteraction, isFileCandidate, shouldDisambiguate, openPathPicker]);

  // Nome di pacchetto/estensione -> grassetto
  if (isPackageNameType) {
    return <strong>{cleanCode}</strong>;
  }

  // Path o path-like -> chip evidenziato (inline)
  if (isPathOnly) {
    return (
      <span
        className="inline-block px-2 py-0.5 rounded text-gray-700 font-mono text-sm"
        title="Percorso"
        style={{
          backgroundColor: '#ececec',
          fontFamily: '"Fira Code", monospace',
        }}
      >
        {cleanCode}
      </span>
    );
  }

  // Inline code standard
  if (inline) {
    return (
      <code
        className="bg-gray-200 px-1 py-0.5 rounded text-gray-800"
        style={{
          fontFamily: '"Fira Code", monospace',
          fontFeatureSettings: '"liga" 0',
          fontVariantLigatures: 'none',
          textRendering: 'optimizeLegibility',
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale'
        }}
        {...props}
      >
        {children}
      </code>
    );
  }

  // Mostra UI auto-capture solo per file candidati
  const showAutoCaptureUI = isAutoCaptureEnabled && hasActiveProject && isFileCandidate;
  const showHeader = true; // stile chatbot: header visibile sui blocchi multi-linea

  return (
    <pre
      className={`block relative my-3 w-full max-w-full transition-all bg-transparent m-0 p-0 overflow-hidden ${
        showAutoCaptureUI ? 'cursor-pointer' : ''
      } ${autoSaved ? 'ring-2 ring-green-400/50' : ''}`}
      data-language={language || 'text'}
      onClick={showAutoCaptureUI ? handleClick : undefined}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      style={{
        fontFamily: 'inherit',
        fontSize: 'inherit',
        lineHeight: 'inherit',
      }}
    >
      <div className="block text-gray-800 rounded-lg overflow-hidden w-full" style={{ backgroundColor: '#f9f9f9' }}>
        {/* Header */}
        {showHeader && (
          <div className="flex justify-between items-center px-3 py-1.5 border-b border-gray-200 w-full">
            <div className="flex items-center min-w-0">
              <span className="text-xs text-gray-600 font-mono">{language || 'text'}</span>
              {filePath && (
                <span
                  className="ml-3 text-[11px] text-gray-500 font-mono truncate inline-block align-middle"
                  title={filePath}
                  style={{ maxWidth: '60ch' }}
                >
                  {filePath}
                </span>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopy();
              }}
              disabled={copied}
              className={`px-3 py-1 text-xs rounded transition-colors ml-2 ${
                copied 
                  ? 'bg-green-500 text-white' 
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              type="button"
              aria-label="Copia codice"
              title="Copia codice"
            >
              {copied ? '✓ Copiato' : 'Copia'}
            </button>
            {(language === 'html' || (filePath && filePath.endsWith('.html'))) && (
              <button
                onClick={(e)=>{ e.stopPropagation(); setIsPreviewOpen(true); }}
                className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
                title="Anteprima"
                type="button"
              >Preview</button>
            )}
            {isAutoCaptureEnabled && isFileCandidate && (
              <button
                onClick={(e)=>{ e.stopPropagation(); openPathPicker(); }}
                className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
                title="Imposta percorso file"
                type="button"
              >Path…</button>
            )}
          </div>
        )}

        {/* Contenuto */}
        <div className="block codeblock-wrapper w-full max-w-full overflow-x-auto">
          <div className="block codeblock-scroll-container w-full max-w-full overflow-x-auto">
            <div className="syntax-highlighter w-full" style={{ display: 'block' }}>
              <SyntaxHighlighter
                language={language || 'text'}
                style={prism}
                customStyle={{
                  margin: 0,
                  borderRadius: 0,
                  background: 'transparent',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  fontFamily: '"Fira Code", "Consolas", "Monaco", "Andale Mono", "Ubuntu Mono", monospace',
                  fontFeatureSettings: '"liga" 0',
                  fontVariantLigatures: 'none',
                  display: 'block',
                  width: '100%',
                  whiteSpace: 'pre',
                  overflowX: 'auto',
                  textRendering: 'optimizeLegibility',
                  WebkitFontSmoothing: 'antialiased',
                  MozOsxFontSmoothing: 'grayscale',
                  padding: '0.75rem'
                }}
                PreTag="div"
                CodeTag="code"
                showLineNumbers={false}
              >
                {cleanCode}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>

        {/* Footer auto-capture */}
        {showAutoCaptureUI && filePath && (
          <div className="flex justify-center items-center px-3 py-1 border-t border-gray-200 bg-gray-50 text-xs">
            <span className="text-green-600">✅ Pronto per il salvataggio automatico</span>
          </div>
        )}

        {/* Path Picker Modal */}
        {isPathPickerOpen && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center" onClick={()=>setIsPathPickerOpen(false)}>
            <div className="bg-white rounded shadow-lg p-3 w-[420px]" onClick={(e)=>e.stopPropagation()}>
              <div className="text-sm font-semibold mb-2">Imposta percorso file</div>
              <input
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono mb-2"
                placeholder="es. src/components/Button.tsx"
                value={tempPath}
                onChange={(e)=>setTempPath(e.target.value)}
              />
              {candidates && candidates.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-gray-500 mb-1">Suggerimenti</div>
                  <div className="max-h-28 overflow-auto border border-gray-100 rounded">
                    {[...candidates].sort((a,b)=>b.score-a.score).map((c,i)=> (
                      <button
                        key={i}
                        className="w-full text-left px-2 py-1 text-xs hover:bg-gray-100 font-mono"
                        onClick={()=>setTempPath(c.path)}
                        type="button"
                      >{c.path} <span className="text-gray-400">({c.score})</span></button>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button className="px-3 py-1 text-xs bg-gray-200 rounded" onClick={()=>setIsPathPickerOpen(false)} type="button">Annulla</button>
                <button className="px-3 py-1 text-xs bg-blue-600 text-white rounded" onClick={()=> tempPath && saveWithPath(tempPath, false)} type="button">Salva</button>
              </div>
            </div>
          </div>
        )}
        {/* Preview Modal */}
        <PreviewModal
          isOpen={isPreviewOpen}
          onClose={()=>setIsPreviewOpen(false)}
          language={language}
          code={cleanCode}
          filePath={filePath}
          projectFiles={props.projectFiles as any}
        />
      </div>
    </pre>
  );
});

CodeBlock.displayName = 'CodeBlock';

export default CodeBlock;
