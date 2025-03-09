import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface File {
  path: string;
  content: string;
  language: string;
}

interface CodeViewerProps {
  file: File | null;
}

export default function CodeViewer({ file }: CodeViewerProps) {
  // Map file extensions to syntax highlighter language names
  const getLanguage = (ext: string): string => {
    const langMap: Record<string, string> = {
      js: 'javascript',
      ts: 'typescript',
      jsx: 'jsx',
      tsx: 'tsx',
      py: 'python',
      html: 'html',
      css: 'css',
      json: 'json',
      md: 'markdown',
    };
    
    return langMap[ext] || ext;
  };

  if (!file) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        No file selected. Select a file from the file browser.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="mb-2 text-sm font-medium truncate">{file.path}</div>
      <div className="flex-1 overflow-auto rounded border">
        <SyntaxHighlighter
          language={getLanguage(file.language)}
          style={vscDarkPlus}
          customStyle={{ 
            margin: 0, 
            height: '100%',
            backgroundColor: 'hsl(var(--muted))',
            fontSize: '0.875rem',
            borderRadius: '0.25rem'
          }}
          showLineNumbers
        >
          {file.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}