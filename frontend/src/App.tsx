import { useState } from 'react';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import StageResearch from './components/StageResearch';
import StageDraft from './components/StageDraft';
import StageStyle from './components/StageStyle';
import StagePrompts from './components/StagePrompts';
import StageImages from './components/StageImages';
import StageTypography from './components/StageTypography';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';
import ProjectHome from './components/ProjectHome';
import NewProjectModal from './components/NewProjectModal';
import TemplatesPage from './components/TemplatesPage';
import { useDarkMode } from './hooks/useDarkMode';

function AppContent() {
  const {
    projects,
    projectsLoading,
    currentProject,
    error,
    setError,
    openProject,
    closeProject,
    createNewProject,
    deleteProject,
    goToStage,
  } = useProject();

  const { isDark, toggle: toggleDark } = useDarkMode();
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showTemplatesPage, setShowTemplatesPage] = useState(false);

  const currentStage = currentProject?.current_stage ?? 1;

  const renderCurrentStage = () => {
    switch (currentStage) {
      case 1: return <StageResearch />;
      case 2: return <StageDraft />;
      case 3: return <StageStyle />;
      case 4: return <StagePrompts />;
      case 5: return <StageImages />;
      case 6: return <StageTypography />;
      default: return <StageResearch />;
    }
  };

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden">
        <Header
          projectName={currentProject?.name ?? null}
          onBack={currentProject ? closeProject : null}
          isDark={isDark}
          onToggleDark={toggleDark}
        />

        {currentProject && (
          <StageIndicator currentStage={currentStage} onStageClick={goToStage} />
        )}

        <main className="flex-1 min-h-0 overflow-y-auto">
          {error && (
            <div className="mx-4 mt-4 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200"
              >
                Dismiss
              </button>
            </div>
          )}

          {currentProject ? (
            <div className="px-4 py-6">
              <div className="max-w-6xl mx-auto">
                {renderCurrentStage()}
              </div>
            </div>
          ) : (
            <ProjectHome
              projects={projects}
              loading={projectsLoading}
              onOpen={openProject}
              onNewProject={() => setShowNewProjectModal(true)}
              onDelete={deleteProject}
              onTemplates={() => setShowTemplatesPage(true)}
            />
          )}
        </main>
      </div>

      {showNewProjectModal && (
        <NewProjectModal
          onClose={() => setShowNewProjectModal(false)}
          onCreate={async (templateId) => {
            await createNewProject(templateId);
            setShowNewProjectModal(false);
          }}
        />
      )}

      {showTemplatesPage && (
        <TemplatesPage onClose={() => setShowTemplatesPage(false)} />
      )}
    </>
  );
}

function App() {
  return (
    <ProjectProvider>
      <AppContent />
    </ProjectProvider>
  );
}

export default App;
