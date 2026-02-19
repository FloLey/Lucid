import type { ReactNode } from 'react';

interface StageLayoutProps {
  leftPanel: ReactNode;
  rightPanel: ReactNode;
}

export default function StageLayout({ leftPanel, rightPanel }: StageLayoutProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full min-h-0">
      <div className="space-y-6 overflow-y-auto min-h-0">
        {leftPanel}
      </div>
      <div className="flex flex-col min-h-0">
        {rightPanel}
      </div>
    </div>
  );
}
