import { useState } from 'react';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import Stage1 from './components/Stage1';
import Stage2 from './components/Stage2';
import Stage3 from './components/Stage3';
import Stage4 from './components/Stage4';
import Stage5 from './components/Stage5';
import Header from './components/Header';
import StageIndicator from './components/StageIndicator';
import ProjectHome from './components/ProjectHome';
import NewProjectModal from './components/NewProjectModal';
import TemplatesPage from './components/TemplatesPage';

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

  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showTemplatesPage, setShowTemplatesPage] = useState(false);

  const currentStage = currentProject?.current_stage ?? 1;

  const renderCurrentStage = () => {
    switch (currentStage) {
      case 1: return <Stage1 />;
      case 2: return <Stage2 />;
      case 3: return <Stage3 />;
      case 4: return <Stage4 />;
      case 5: return <Stage5 />;
      default: return <Stage1 />;
    }
  };

  return (
    <>
      <div className="h-screen flex flex-col overflow-hidden">
        <Header
          projectName={currentProject?.name ?? null}
          onBack={currentProject ? closeProject : null}
        />

        {currentProject && (
          <StageIndicator currentStage={currentStage} onStageClick={goToStage} />
        )}

        <main className="flex-1 min-h-0 overflow-y-auto">
          {error && (
            <div className="mx-4 mt-4 p-4 bg-red-100 text-red-700 rounded-lg">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 text-red-500 hover:text-red-700"
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
