import React from 'react';
import { IConversation } from '../db'; // Dexie DB interface

interface ConversationListSidebarProps {
  conversations: IConversation[];
  selectedConversationId?: number | null;
  onSelectConversation: (conversation: IConversation) => void;
  onNewConversation: () => void;
  onDeleteConversation: (conversationId: number) => void;
}

const ConversationListSidebar: React.FC<ConversationListSidebarProps> = ({
  conversations,
  selectedConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}) => {
  return (
    <div className="flex flex-col h-full mt-4">
      <button
        onClick={onNewConversation}
        className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded mb-4 transition duration-150"
      >
        New Chat
      </button>
      <h2 className="text-lg font-semibold mb-2 text-gray-300">Conversations</h2>
      <div className="flex-grow overflow-y-auto space-y-2 pr-1">
        {conversations.length === 0 && (
          <p className="text-gray-400 text-sm">No conversations yet.</p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`p-3 rounded-lg cursor-pointer hover:bg-gray-700 transition duration-150 ${
              selectedConversationId === conv.id ? 'bg-gray-750 ring-2 ring-blue-500' : 'bg-gray-800'
            }`}
            onClick={() => onSelectConversation(conv)}
          >
            <div className="flex justify-between items-start">
              <h3 className="text-sm font-medium text-gray-100 truncate pr-2" title={conv.title}>
                {conv.title || 'Untitled Conversation'}
              </h3>
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Prevent selecting conversation when deleting
                  if (window.confirm(`Are you sure you want to delete "${conv.title || 'this conversation'}"?`)) {
                    onDeleteConversation(conv.id!);
                  }
                }}
                className="text-red-400 hover:text-red-300 text-xs p-1 rounded hover:bg-gray-600"
                title="Delete conversation"
              >
                {/* Simple X icon, replace with SVG later if desired */}
                &#x2715;
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Model: {conv.model}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {new Date(conv.updatedAt).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConversationListSidebar;
