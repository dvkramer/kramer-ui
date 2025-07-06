import React, { useState } from 'react';
import { IMessage } from '../db';

interface MessageItemProps {
  message: IMessage;
  onEdit: (messageId: number, newContent: string) => void;
  isStreaming?: boolean; // Optional: to indicate the assistant message is still streaming
}

const MessageItem: React.FC<MessageItemProps> = ({ message, onEdit, isStreaming }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(message.content);

  const isUser = message.role === 'user';

  const handleSaveEdit = () => {
    if (editedContent.trim() !== message.content) {
      onEdit(message.id!, editedContent.trim());
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedContent(message.content);
    setIsEditing(false);
  };

  // Basic markdown-like rendering for newlines.
  // For full markdown, a library like 'react-markdown' would be used.
  const renderContent = (content: string) => {
    return content.split('\n').map((line, index, array) => (
      <React.Fragment key={index}>
        {line}
        {index < array.length - 1 && <br />}
      </React.Fragment>
    ));
  };


  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-xl lg:max-w-2xl xl:max-w-3xl px-4 py-3 rounded-lg shadow ${
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-600 text-gray-100'
        }`}
      >
        {isEditing ? (
          <div>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="w-full p-2 rounded bg-gray-500 text-white focus:outline-none focus:ring-1 focus:ring-blue-400"
              rows={Math.min(10, editedContent.split('\n').length + 1)}
            />
            <div className="mt-2 flex justify-end space-x-2">
              <button
                onClick={handleCancelEdit}
                className="px-3 py-1 text-xs bg-gray-400 hover:bg-gray-500 text-black rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-3 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="prose prose-sm prose-invert max-w-none break-words">
                {renderContent(message.content)}
                {isStreaming && <span className="inline-block w-2 h-4 bg-white ml-1 animate-pulse"></span>}
            </div>
            <div className="mt-2 flex items-center justify-between">
                <p className="text-xs opacity-70">
                {new Date(message.createdAt).toLocaleTimeString()}
                </p>
                {isUser && !isStreaming && ( // Can only edit user messages, and not if something is streaming (i.e. app is busy)
                <button
                    onClick={() => setIsEditing(true)}
                    className="ml-2 px-2 py-0.5 text-xs text-gray-300 hover:text-white hover:bg-gray-500 rounded"
                    title="Edit message"
                >
                    Edit
                </button>
                )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MessageItem;
