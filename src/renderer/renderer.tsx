import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css'; // Tailwind CSS
import { ollamaApi, OllamaModel } from './services/OllamaApi'; // Assuming OllamaApi.ts is in services
import ConversationListSidebar from './components/ConversationListSidebar';
import ChatWindow from './components/ChatWindow';
import ModelSelector from './components/ModelSelector';
import { IConversation, db } from './db'; // Dexie DB

// Define the electronAPI property on the Window interface
declare global {
  interface Window {
    electronAPI?: {
      invoke: (channel: string, ...args: any[]) => Promise<any>;
      on: (channel: string, listener: (event: Electron.IpcRendererEvent, ...args: any[]) => void) => () => void;
    };
  }
}

const App: React.FC = () => {
  const [ollamaConnected, setOllamaConnected] = useState<boolean>(false);
  const [connectionStatusMessage, setConnectionStatusMessage] = useState<string>('Connecting to Ollama...');
  const [availableModels, setAvailableModels] = useState<OllamaModel[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<IConversation | null>(null);
  const [conversations, setConversations] = useState<IConversation[]>([]);
  // Current model for NEW chats or if a conversation doesn't have one specified yet
  const [currentGlobalModel, setCurrentGlobalModel] = useState<string>('');

  useEffect(() => {
    const checkConnectionAndFetchData = async () => {
      const connected = await ollamaApi.checkConnection();
      setOllamaConnected(connected);
      if (connected) {
        setConnectionStatusMessage('Connected to Ollama');
        try {
          const modelsResponse = await ollamaApi.listModels();
          setAvailableModels(modelsResponse.models || []);
          if (modelsResponse.models && modelsResponse.models.length > 0) {
            // Set a default model if none is set, or from local storage later
            if(!currentGlobalModel) setCurrentGlobalModel(modelsResponse.models[0].name);
          } else {
             setConnectionStatusMessage('Connected to Ollama, but no models found. Pull a model to start.');
          }
        } catch (error) {
          console.error('Failed to fetch models:', error);
          setConnectionStatusMessage('Error fetching models from Ollama.');
          setAvailableModels([]);
        }
        loadConversations();
      } else {
        setConnectionStatusMessage('Failed to connect to Ollama. Ensure Ollama is running.');
        setAvailableModels([]);
      }
    };

    checkConnectionAndFetchData();
    // Optionally, set up a poller to check connection periodically or rely on user action to retry
  }, []);

  const loadConversations = async () => {
    const convs = await db.conversations.orderBy('updatedAt').reverse().toArray();
    setConversations(convs);
  };

  const handleSelectConversation = (conversation: IConversation) => {
    setSelectedConversation(conversation);
    // When a conversation is selected, its model should become the "active" model for the chat window
    if (conversation.model) {
        setCurrentGlobalModel(conversation.model);
    }
  };

  const handleNewConversation = async () => {
    if (!currentGlobalModel && availableModels.length > 0) {
      // If no global model is set, pick the first available one
      setCurrentGlobalModel(availableModels[0].name);
    }
    // Create a placeholder new conversation or wait for the first message
    // For now, just clear selection and ensure a model is ready
    setSelectedConversation(null);
    // A new conversation will be formally created in DB upon sending the first message.
    // The ChatWindow will use currentGlobalModel for this new (pending) conversation.
    console.log("Starting new conversation with model:", currentGlobalModel || "No model selected yet");
  };

  const handleDeleteConversation = async (conversationId: number) => {
    try {
      await db.transaction('rw', db.conversations, db.messages, async () => {
        await db.messages.where('conversationId').equals(conversationId).delete();
        await db.conversations.delete(conversationId);
      });
      await loadConversations(); // Refresh list
      if (selectedConversation?.id === conversationId) {
        setSelectedConversation(null); // Clear selection if deleted conv was active
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      // Show error to user
    }
  };


  return (
    <div className="flex h-screen bg-gray-800 text-white">
      {/* Sidebar */}
      <div className="w-1/4 min-w-[280px] max-w-[400px] bg-gray-900 p-4 flex flex-col">
        <div className="mb-4">
          <h1 className="text-2xl font-semibold mb-1">Ollama Chat</h1>
          <p className={`text-xs ${ollamaConnected ? 'text-green-400' : 'text-red-400'}`}>
            {connectionStatusMessage}
          </p>
        </div>

        {ollamaConnected && availableModels.length > 0 && (
          <ModelSelector
            models={availableModels}
            selectedModel={currentGlobalModel}
            onSelectModel={setCurrentGlobalModel}
          />
        )}
        {ollamaConnected && availableModels.length === 0 && (
            <p className="text-sm text-yellow-400 my-2">No local models found. Go to Ollama to pull a model (e.g. `ollama pull llama3`).</p>
        )}


        <ConversationListSidebar
          conversations={conversations}
          selectedConversationId={selectedConversation?.id}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <ChatWindow
          conversation={selectedConversation}
          ollamaModels={availableModels}
          selectedModelName={selectedConversation?.model || currentGlobalModel} // Model for the current/new chat
          onConversationUpdate={loadConversations} // To refresh list after title generation/model change
          key={selectedConversation?.id || 'new'} // Force re-render on new/changed conversation
        />
      </div>
    </div>
  );
};

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
} else {
  console.error('Root element not found');
}
