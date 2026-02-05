interface StageIndicatorProps {
  currentStage: number;
}

const stages = [
  { num: 1, name: 'Draft', desc: 'Create slide texts' },
  { num: 2, name: 'Prompts', desc: 'Generate image prompts' },
  { num: 3, name: 'Images', desc: 'Generate backgrounds' },
  { num: 4, name: 'Design', desc: 'Apply typography' },
];

export default function StageIndicator({ currentStage }: StageIndicatorProps) {
  return (
    <div className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {stages.map((stage, index) => (
            <div key={stage.num} className="flex items-center">
              <div className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    stage.num === currentStage
                      ? 'bg-lucid-600 text-white'
                      : stage.num < currentStage
                      ? 'bg-lucid-100 text-lucid-700'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {stage.num < currentStage ? '✓' : stage.num}
                </div>
                <div className="hidden sm:block">
                  <div
                    className={`text-sm font-medium ${
                      stage.num === currentStage
                        ? 'text-lucid-700'
                        : stage.num < currentStage
                        ? 'text-gray-600'
                        : 'text-gray-400'
                    }`}
                  >
                    {stage.name}
                  </div>
                  <div className="text-xs text-gray-400">{stage.desc}</div>
                </div>
              </div>
              {index < stages.length - 1 && (
                <div
                  className={`hidden sm:block w-16 md:w-24 lg:w-32 h-0.5 mx-4 ${
                    stage.num < currentStage ? 'bg-lucid-300' : 'bg-gray-200'
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
