"use client";

import React from 'react';
import { SandpackProvider, SandpackLayout, SandpackCodeEditor, SandpackPreview } from "@codesandbox/sandpack-react";

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  language: string;
  code: string;
  filePath?: string | null;
  projectFiles?: Array<{ path: string; content: string; language: string }>;
}

const splitPath = (p: string) => p.split('/').filter(Boolean);
const joinPath = (parts: string[]) => '/' + parts.join('/');
const dirname = (p: string) => '/' + splitPath(p).slice(0, -1).join('/');

const relativePath = (fromDir: string, toPath: string) => {
  const fromParts = splitPath(fromDir);
  const toParts = splitPath(toPath);
  let i = 0;
  while (i < fromParts.length && i < toParts.length && fromParts[i] === toParts[i]) i++;
  const up = new Array(fromParts.length - i).fill('..');
  const down = toParts.slice(i);
  const rel = [...up, ...down].join('/');
  return rel || '.';
};

const preprocessCode = (code: string, currentFilePath?: string | null, projectFiles?: Array<{ path: string; content: string; language: string }>) => {
  const extraFiles: Record<string, { code: string }> = {};
  let transformed = code;
  const cur = currentFilePath ? ('/' + normalizePath(currentFilePath)) : undefined;
  const curDir = cur ? dirname(cur) : '/';

  // Stub Next.js modules
  if (/from\s+['"]next\/link['"]/.test(transformed)) {
    transformed = transformed.replace(/import\s+Link\s+from\s+['"]next\/link['"];?\s*/g,
      "const Link: any = (props: any) => <a href={props.href} style={props.style} onClick={(e:any)=>{e.preventDefault(); if(typeof props.href==='string'){ window.location.hash = props.href.startsWith('#') ? props.href : ('#'+props.href); }}}>{props.children}</a>;\n");
  }
  if (/from\s+['"]next\/image['"]/.test(transformed)) {
    transformed = transformed.replace(/import\s+Image\s+from\s+['"]next\/image['"];?\s*/g,
      "const Image: any = (props: any) => <img {...props} />;\n");
  }
  if (/from\s+['"]next\/head['"]/.test(transformed)) {
    transformed = transformed.replace(/import\s+Head\s+from\s+['"]next\/head['"];?\s*/g,
      "const Head: any = ({children}: any) => <>{children}</>;\n");
  }
  if (/from\s+['"]next\/navigation['"]/.test(transformed)) {
    transformed = transformed.replace(/import\s+\{([^}]+)\}\s+from\s+['"]next\/navigation['"];?\s*/g,
      "const useRouter = () => ({ push: (p:any)=>{ window.location.hash = typeof p==='string'? (p.startsWith('#')?p:('#'+p)) : '#/'; } });\nconst usePathname = () => window.location.hash.replace(/^#/, '') || '/';\nconst useSearchParams = () => new URLSearchParams((window.location.hash.split('?')[1]||''));\n");
  }
  if (/from\s+['"]next\/router['"]/.test(transformed)) {
    transformed = transformed.replace(/import\s+\{?\s*useRouter\s*\}?\s+from\s+['"]next\/router['"];?\s*/g,
      "const useRouter = () => ({ push: (p:any)=>{ window.location.hash = typeof p==='string'? (p.startsWith('#')?p:('#'+p)) : '#/'; } });\n");
  }

  // Replace alias @/ with ./ (temporaneo, poi sistemiamo i relativi)
  if (/from\s+['"]@\//.test(transformed)) {
    transformed = transformed.replace(/from\s+['"]@\/(.*?)['"]/g, (m, p1) => `from './${p1}'`);
  }

  // Aggiusta import relativi per components/lib quando il file è in src/app/**/*
  if (cur && /^\/src\/app(\/|$)/.test(cur)) {
    // ./components/* -> relativo a /src/components
    transformed = transformed.replace(/from\s+['"]\.\/components\/(.*?)['"]/g, (m, p1) => {
      const target = '/src/components/' + p1;
      const rel = relativePath(curDir, target);
      return `from '${rel}'`;
    });
    // ./lib/* -> relativo a /src/lib
    transformed = transformed.replace(/from\s+['"]\.\/lib\/(.*?)['"]/g, (m, p1) => {
      const target = '/src/lib/' + p1;
      const rel = relativePath(curDir, target);
      return `from '${rel}'`;
    });
  }

  // Stub Hello solo se manca nei projectFiles
  const hasHello = (projectFiles || []).some(f => normalizePath(f.path).match(/^src\/components\/Hello\.(tsx|jsx|ts|js)$/));
  if (/from\s+['"][\.\/]*components\/Hello['"]/.test(transformed) && !hasHello) {
    extraFiles['/src/components/Hello.tsx'] = { code: "export default function Hello({name}: {name?: string}) { return <div>Hello {name || 'World'}</div> }" };
  }

  return { transformed, extraFiles };
};

const normalizePath = (p: string) => p.replace(/^\/+/, '');

const buildFilesForSandpack = (
  language: string,
  code: string,
  filePath?: string | null,
  projectFiles?: Array<{ path: string; content: string; language: string }>
) => {
  const files: Record<string, { code: string }> = {};
  const { transformed, extraFiles } = preprocessCode(code, filePath, projectFiles);
  Object.assign(files, extraFiles);

  // Porta dentro anche i file del progetto
  if (projectFiles && projectFiles.length) {
    for (const f of projectFiles) {
      if (!f.path || !f.content) continue;
      const rel = '/' + normalizePath(f.path);
      files[rel] = { code: f.content };
    }
  }

  const reactBootstrap = (componentImportPath: string) => `import React from 'react';
import { createRoot } from 'react-dom/client';
import Component from '${componentImportPath}';

const rootEl = document.getElementById('root');
if (rootEl) {
  const root = createRoot(rootEl);
  root.render(<Component />);
}`;

  if (filePath && (filePath.endsWith('.tsx') || filePath.endsWith('.jsx') || filePath.endsWith('.ts') || filePath.endsWith('.js'))) {
    const relPath = normalizePath(filePath);
    files[`/${relPath}`] = { code: transformed };
    files['/index.tsx'] = { code: reactBootstrap(`./${relPath}`) };
  } else {
    // Fallback: metti il codice come App e fai il bootstrap
    files['/App.tsx'] = { code: transformed.includes('export default') ? transformed : `export default function App(){\nreturn (\n<>\n${transformed}\n</>\n);\n}` };
    files['/index.tsx'] = { code: reactBootstrap('./App') };
  }
  return files;
};

// Rileva dipendenze non relative in modo sicuro per Sandpack
const detectDependencies = (source: string) => {
  const baseDeps: Record<string, string> = {
    react: '18.2.0',
    'react-dom': '18.2.0',
    tslib: '2.6.3',
  };

  const knownVersions: Record<string, string> = {
    clsx: '2.1.1',
    'tailwind-merge': '2.5.4',
    axios: '1.7.7',
    swr: '2.2.5',
    zod: '3.23.8',
    zustand: '4.5.5',
    dayjs: '1.11.11',
    'date-fns': '3.6.0',
    uuid: '9.0.1',
    lodash: '4.17.21',
    'lodash-es': '4.17.21',
    'lucide-react': '0.469.0',
  };

  const isExternal = (mod: string) => {
    if (!mod) return false;
    if (mod.startsWith('.') || mod.startsWith('/') || mod.startsWith('@/')) return false;
    if (mod.startsWith('http://') || mod.startsWith('https://')) return false;
    if (mod.startsWith('next/')) return false; // non supportiamo runtime Next
    return true;
  };

  const hasFileExtension = (s: string) => /\.(css|scss|sass|less|json|svg|png|jpg|jpeg|gif|webp|avif|ico|md|txt)$/i.test(s);

  const normalize = (mod: string) => {
    if (mod === 'react/jsx-runtime') return 'react';
    if (mod.startsWith('@')) {
      const parts = mod.split('/');
      return parts.length >= 2 ? parts.slice(0, 2).join('/') : mod;
    }
    const idx = mod.indexOf('/');
    return idx > 0 ? mod.slice(0, idx) : mod;
  };

  const modules = new Set<string>();
  const patterns = [
    /from\s+['"]([^'"\n]+)['"]/g, // import ... from 'mod'
    /import\s+['"]([^'"\n]+)['"]/g, // import 'mod'
    /require\(\s*['"]([^'"\n]+)['"]\s*\)/g, // require('mod')
  ];

  for (const re of patterns) {
    let m: RegExpExecArray | null;
    while ((m = re.exec(source))) {
      const raw = m[1];
      if (!isExternal(raw)) continue;
      if (hasFileExtension(raw)) continue;
      const mod = normalize(raw);
      if (mod && isExternal(mod)) modules.add(mod);
    }
  }

  const deps: Record<string, string> = { ...baseDeps };
  // Limita il numero massimo di dipendenze extra per affidabilità CDN
  const MAX_EXTRA = 10;
  let count = 0;
  for (const mod of modules) {
    if (mod in deps) continue;
    const version = knownVersions[mod] || 'latest';
    deps[mod] = version;
    count++;
    if (count >= MAX_EXTRA) break;
  }
  return deps;
};

export default function PreviewModal({ isOpen, onClose, language, code, filePath, projectFiles }: PreviewModalProps) {
  if (!isOpen) return null;

  const isHtml = language === 'html' || (filePath && filePath.endsWith('.html'));
  const isCss = language === 'css' || (filePath && filePath.endsWith('.css'));
  const isJsTs = ['js','ts','tsx','jsx','javascript','typescript'].includes(language) || (filePath && /\.(tsx?|jsx?)$/.test(filePath));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-3 border-b">
          <div className="text-sm font-semibold">Anteprima</div>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-800">✕</button>
        </div>
        <div className="flex-1 overflow-hidden">
          {isHtml ? (
            <iframe
              className="w-full h-full"
              sandbox="allow-scripts"
              srcDoc={code}
              title="Preview"
            />
          ) : isCss ? (
            <iframe
              className="w-full h-full"
              sandbox="allow-scripts"
              srcDoc={`<!doctype html><html><head><style>${code}</style></head><body><div style='padding:16px;font-family:sans-serif'>CSS preview</div></body></html>`}
              title="Preview"
            />
          ) : isJsTs ? (
            <div className="h-full min-h-0">
              <SandpackProvider 
                template="react-ts" 
                files={buildFilesForSandpack(language, code, filePath || undefined, projectFiles)} 
                className="h-full" 
                style={{ height: '100%', minHeight: 0 }}
                customSetup={{
                  dependencies: detectDependencies(((projectFiles||[]).map(f=>f.content).join('\n')) + '\n' + code)
                }}
              >
                <SandpackLayout className="h-full" style={{ height: '100%', minHeight: 0 }}>
                  <SandpackCodeEditor showLineNumbers wrapContent showTabs={true} style={{ height: '100%', minHeight: 0 }} />
                  <SandpackPreview showNavigator={true} style={{ height: '100%', minHeight: 0 }} />
                </SandpackLayout>
              </SandpackProvider>
            </div>
          ) : (
            <div className="p-4 text-sm text-gray-600">Anteprima non disponibile per questo tipo di codice.</div>
          )}
        </div>
      </div>
    </div>
  );
}
