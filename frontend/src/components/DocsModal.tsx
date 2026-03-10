import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface DocsModalProps {
  onClose: () => void;
}

interface Heading {
  level: number;
  text: string;
  id: string;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_]+/g, '-');
}

function parseHeadings(markdown: string): Heading[] {
  const matches = [...markdown.matchAll(/^(#{1,3})\s+(.+)$/gm)];
  return matches.map((m) => ({
    level: m[1].length,
    text: m[2].trim(),
    id: slugify(m[2].trim()),
  }));
}

export default function DocsModal({ onClose }: DocsModalProps) {
  const [markdown, setMarkdown] = useState('');
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [activeId, setActiveId] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);

  // Fetch docs on mount
  useEffect(() => {
    fetch('/docs/user-guide.md')
      .then((r) => r.text())
      .then((text) => {
        setMarkdown(text);
        setHeadings(parseHeadings(text));
      })
      .catch(() => setMarkdown('Failed to load documentation.'));
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  // Track active heading via IntersectionObserver
  useEffect(() => {
    if (!contentRef.current || headings.length === 0) return;
    const elements = headings
      .map((h) => document.getElementById(h.id))
      .filter(Boolean) as HTMLElement[];

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      { root: contentRef.current, rootMargin: '0px 0px -70% 0px', threshold: 0 }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [headings, markdown]);

  const scrollToHeading = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (el && contentRef.current) {
      // Scroll within the content panel
      const panelTop = contentRef.current.getBoundingClientRect().top;
      const elTop = el.getBoundingClientRect().top;
      contentRef.current.scrollBy({ top: elTop - panelTop - 16, behavior: 'smooth' });
    }
  }, []);

  const components = {
    h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
      const text = typeof children === 'string' ? children : String(children ?? '');
      const id = slugify(text);
      return (
        <h1 id={id} className="text-2xl font-bold text-gray-900 dark:text-white mt-8 mb-3" {...props}>
          {children}
        </h1>
      );
    },
    h2: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
      const text = typeof children === 'string' ? children : String(children ?? '');
      const id = slugify(text);
      return (
        <h2 id={id} className="text-lg font-semibold text-gray-800 dark:text-gray-100 mt-6 mb-2 pb-1 border-b border-gray-200 dark:border-gray-700" {...props}>
          {children}
        </h2>
      );
    },
    h3: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
      const text = typeof children === 'string' ? children : String(children ?? '');
      const id = slugify(text);
      return (
        <h3 id={id} className="text-base font-semibold text-gray-700 dark:text-gray-200 mt-4 mb-1.5" {...props}>
          {children}
        </h3>
      );
    },
    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed mb-3" {...props}>{children}</p>
    ),
    ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 mb-3 space-y-1 pl-2" {...props}>{children}</ul>
    ),
    ol: ({ children, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
      <ol className="list-decimal list-inside text-sm text-gray-700 dark:text-gray-300 mb-3 space-y-1 pl-2" {...props}>{children}</ol>
    ),
    li: ({ children, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
      <li className="leading-relaxed" {...props}>{children}</li>
    ),
    blockquote: ({ children, ...props }: React.HTMLAttributes<HTMLQuoteElement>) => (
      <blockquote className="border-l-4 border-lucid-400 pl-3 my-3 text-sm text-gray-600 dark:text-gray-400 italic" {...props}>{children}</blockquote>
    ),
    code: ({ children, className, ...props }: React.HTMLAttributes<HTMLElement>) => {
      const isBlock = className?.startsWith('language-');
      return isBlock ? (
        <code className="block bg-gray-100 dark:bg-gray-800 rounded-md p-3 text-xs font-mono text-gray-800 dark:text-gray-200 overflow-x-auto mb-3 whitespace-pre" {...props}>{children}</code>
      ) : (
        <code className="bg-gray-100 dark:bg-gray-800 rounded px-1 py-0.5 text-xs font-mono text-gray-800 dark:text-gray-200" {...props}>{children}</code>
      );
    },
    pre: ({ children, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
      <pre className="mb-3" {...props}>{children}</pre>
    ),
    table: ({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
      <div className="overflow-x-auto mb-4">
        <table className="w-full text-sm border-collapse" {...props}>{children}</table>
      </div>
    ),
    thead: ({ children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
      <thead className="bg-gray-50 dark:bg-gray-800" {...props}>{children}</thead>
    ),
    th: ({ children, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
      <th className="text-left px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700" {...props}>{children}</th>
    ),
    td: ({ children, ...props }: React.HTMLAttributes<HTMLTableCellElement>) => (
      <td className="px-3 py-2 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 align-top" {...props}>{children}</td>
    ),
    hr: (props: React.HTMLAttributes<HTMLHRElement>) => (
      <hr className="border-gray-200 dark:border-gray-700 my-6" {...props} />
    ),
    a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-lucid-600 dark:text-lucid-400 hover:underline" {...props}>{children}</a>
    ),
    strong: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <strong className="font-semibold text-gray-900 dark:text-white" {...props}>{children}</strong>
    ),
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Documentation"
    >
      <div
        className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-lucid-600 dark:text-lucid-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span className="font-semibold text-gray-900 dark:text-white">Documentation</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close documentation"
            className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* TOC sidebar */}
          <nav
            className="w-48 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 overflow-y-auto py-4 px-3"
            aria-label="Table of contents"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3 px-1">
              Contents
            </p>
            <ul className="space-y-0.5">
              {headings.map((h) => (
                <li key={h.id}>
                  <button
                    onClick={() => scrollToHeading(h.id)}
                    className={[
                      'w-full text-left rounded px-2 py-1 text-xs transition-colors leading-snug',
                      h.level === 1 ? 'font-semibold' : '',
                      h.level === 3 ? 'pl-4' : '',
                      activeId === h.id
                        ? 'bg-lucid-50 dark:bg-lucid-900/30 text-lucid-700 dark:text-lucid-300'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100',
                    ].join(' ')}
                  >
                    {h.text}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {/* Content */}
          <div
            ref={contentRef}
            className="flex-1 overflow-y-auto px-8 py-6"
          >
            {markdown ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as never}>
                {markdown}
              </ReactMarkdown>
            ) : (
              <div className="flex items-center justify-center h-32 text-gray-400 dark:text-gray-500 text-sm">
                Loading…
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
