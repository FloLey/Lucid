import { useState } from 'react';
import type { ProjectCard } from '../types';

const STAGE_LABELS: Record<number, string> = {
  1: 'Draft',
  2: 'Style',
  3: 'Prompts',
  4: 'Images',
  5: 'Typography',
};

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

interface ProjectHomeProps {
  projects: ProjectCard[];
  loading: boolean;
  onOpen: (projectId: string) => void;
  onNewProject: () => void;
  onDelete: (projectId: string) => void;
  onTemplates: () => void;
}

export default function ProjectHome({ projects, loading, onOpen, onNewProject, onDelete, onTemplates }: ProjectHomeProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this project? This cannot be undone.')) return;
    setDeletingId(projectId);
    try {
      await onDelete(projectId);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="px-6 py-8 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Your Projects</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Pick up where you left off, or start something new.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onTemplates}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Templates
          </button>
          <button
            onClick={onNewProject}
            className="flex items-center gap-2 px-5 py-2.5 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Project
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
              <div className="bg-gray-200 dark:bg-gray-700" style={{ aspectRatio: '4/5' }} />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-20 h-20 bg-lucid-50 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-10 h-10 text-lucid-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No projects yet</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
            Create your first project to start turning rough drafts into polished carousels.
          </p>
          <button
            onClick={onNewProject}
            className="px-6 py-3 bg-lucid-600 text-white font-medium rounded-lg hover:bg-lucid-700 transition-colors"
          >
            Create your first project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {projects.map((project) => (
            <div
              key={project.project_id}
              onClick={() => onOpen(project.project_id)}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden cursor-pointer hover:shadow-md hover:border-lucid-300 dark:hover:border-lucid-600 transition-all group"
            >
              {/* Thumbnail */}
              <div className="bg-gray-100 dark:bg-gray-700 relative overflow-hidden" style={{ aspectRatio: '4/5' }}>
                {project.thumbnail_url ? (
                  <img
                    src={project.thumbnail_url}
                    alt={project.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-lucid-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                        <span className="text-lucid-600 font-bold text-xl">L</span>
                      </div>
                      <span className="text-xs text-gray-400 dark:text-gray-500">No preview</span>
                    </div>
                  </div>
                )}

                {/* Stage badge */}
                <div className="absolute top-2 left-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-white/90 text-gray-700 shadow-sm">
                    Stage {project.current_stage}: {STAGE_LABELS[project.current_stage] ?? 'Unknown'}
                  </span>
                </div>

                {/* Delete button */}
                <button
                  onClick={(e) => handleDelete(e, project.project_id)}
                  disabled={deletingId === project.project_id}
                  className="absolute top-2 right-2 w-7 h-7 bg-white/90 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-50 transition-all shadow-sm"
                  title="Delete project"
                >
                  {deletingId === project.project_id ? (
                    <svg className="w-3.5 h-3.5 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5 text-gray-500 hover:text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </div>

              {/* Card info */}
              <div className="p-3">
                <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate text-sm">{project.name}</h3>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-500 dark:text-gray-400">{project.slide_count} slides</span>
                  <span className="text-xs text-gray-400 dark:text-gray-500">{formatDate(project.updated_at)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
