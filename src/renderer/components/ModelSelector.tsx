import React from 'react';
import { OllamaModel } from '../services/OllamaApi';

interface ModelSelectorProps {
  models: OllamaModel[];
  selectedModel: string | null;
  onSelectModel: (modelName: string) => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ models, selectedModel, onSelectModel }) => {
  if (!models || models.length === 0) {
    return (
      <div className="my-4">
        <p className="text-sm text-yellow-400">No models available. Pull a model with Ollama.</p>
      </div>
    );
  }

  return (
    <div className="my-4">
      <label htmlFor="model-select" className="block text-sm font-medium text-gray-300 mb-1">
        Select Model:
      </label>
      <select
        id="model-select"
        value={selectedModel || ''}
        onChange={(e) => onSelectModel(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 p-2.5"
      >
        {!selectedModel && <option value="" disabled>-- Select a model --</option>}
        {models.map((model) => (
          <option key={model.name} value={model.name}>
            {model.name} ({formatBytes(model.size)})
          </option>
        ))}
      </select>
      {/* Optional: Add a button here to trigger model pull UI */}
    </div>
  );
};

// Helper function to format bytes into readable sizes
function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default ModelSelector;
