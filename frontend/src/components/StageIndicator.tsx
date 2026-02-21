import { STAGES } from '../constants';

interface StageIndicatorProps {
  currentStage: number;
  onStageClick: (stage: number) => void;
}

export default function StageIndicator({ currentStage, onStageClick }: StageIndicatorProps) {
  return (
    <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {STAGES.map((stage, index) => (
            <div key={stage.number} className="flex items-center">
              <button
                onClick={() => onStageClick(stage.number)}
                className="flex items-center gap-2 group cursor-pointer"
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                    stage.number === currentStage
                      ? 'bg-lucid-600 text-white'
                      : stage.number < currentStage
                      ? 'bg-lucid-100 text-lucid-700 group-hover:bg-lucid-200 dark:bg-lucid-900/40 dark:text-lucid-300'
                      : 'bg-gray-100 text-gray-400 group-hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-500 dark:group-hover:bg-gray-700'
                  }`}
                >
                  {stage.number < currentStage ? '✓' : stage.number}
                </div>
                <div className="hidden sm:block text-left">
                  <div
                    className={`text-sm font-medium transition-colors ${
                      stage.number === currentStage
                        ? 'text-lucid-700 dark:text-lucid-400'
                        : stage.number < currentStage
                        ? 'text-gray-600 dark:text-gray-400 group-hover:text-lucid-600'
                        : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-600'
                    }`}
                  >
                    {stage.name}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">{stage.description}</div>
                </div>
              </button>
              {index < STAGES.length - 1 && (
                <div
                  className={`hidden sm:block w-16 md:w-24 lg:w-32 h-0.5 mx-4 ${
                    stage.number < currentStage ? 'bg-lucid-300' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
