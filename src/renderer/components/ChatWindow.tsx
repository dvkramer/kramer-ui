import React, { useState, useEffect, useRef, useCallback } from 'react';
import { IConversation, IMessage, db } from '../db';
import { ollamaApi, OllamaMessage, OllamaModel, OllamaChatStreamChunk } from '../services/OllamaApi';
import MessageItem from './MessageItem'; // Will be created next

interface ChatWindowProps {
  conversation: IConversation | null; // null for a new chat
  ollamaModels: OllamaModel[]; // All available models
  selectedModelName: string; // Model to be used for this chat (either from conv or global)
  onConversationUpdate: () => void; // Callback to refresh conversation list (e.g., after title/model update)
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  conversation,
  ollamaModels,
  selectedModelName,
  onConversationUpdate,
}) => {
  const [messages, setMessages] = useState<IMessage[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentAssistantMessage, setCurrentAssistantMessage] = useState<string>('');
  const [currentAssistantMessageId, setCurrentAssistantMessageId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentAssistantMessage]);

  const loadMessages = useCallback(async () => {
    if (conversation?.id) {
      const msgs = await db.messages.where('conversationId').equals(conversation.id).sortBy('createdAt');
      setMessages(msgs);
      setCurrentAssistantMessage(''); // Clear any streaming remnants
      setCurrentAssistantMessageId(null);
    } else {
      setMessages([]); // New conversation, clear messages
    }
  }, [conversation?.id]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  const generateTitle = async (firstMessageContent: string, convId: number) => {
    // Simple title: first few words. Could also use Ollama to summarize.
    const words = firstMessageContent.split(' ');
    const title = words.slice(0, 5).join(' ') + (words.length > 5 ? '...' : '');
    await db.conversations.update(convId, { title });
    onConversationUpdate(); // Refresh sidebar
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    if (!selectedModelName) {
      setError("Please select a model first.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setCurrentAssistantMessage('');
    setCurrentAssistantMessageId(null);

    const userMessageContent = inputMessage.trim();
    setInputMessage('');

    let currentConversation = conversation;
    let conversationIdToUse: number;

    try {
      // 1. Save/Update Conversation and User Message
      if (!currentConversation?.id) { // New conversation
        const newConvId = await db.conversations.add({
          title: 'New Conversation...', // Placeholder title
          model: selectedModelName,
          createdAt: new Date(),
          updatedAt: new Date(),
        });
        conversationIdToUse = newConvId;
        await generateTitle(userMessageContent, newConvId); // Generate title from first message
        // Fetch the newly created conversation to make it "current"
        currentConversation = await db.conversations.get(newConvId) || null;

      } else { // Existing conversation
        conversationIdToUse = currentConversation.id;
        // Update model if it changed for this existing conversation
        if (currentConversation.model !== selectedModelName) {
            await db.conversations.update(conversationIdToUse, { model: selectedModelName, updatedAt: new Date() });
        } else {
            await db.conversations.update(conversationIdToUse, { updatedAt: new Date() });
        }
      }

      const userMessage: IMessage = {
        conversationId: conversationIdToUse,
        role: 'user',
        content: userMessageContent,
        createdAt: new Date(),
      };
      const userMessageId = await db.messages.add(userMessage);
      setMessages(prev => [...prev, {...userMessage, id: userMessageId}]);


      // 2. Prepare messages for Ollama API
      const historyForApi: OllamaMessage[] = messages.map(m => ({ role: m.role, content: m.content }));
      historyForApi.push({ role: 'user', content: userMessageContent });

      // 3. Stream response from Ollama
      let assistantResponseContent = '';
      const assistantMessagePlaceholder: IMessage = {
        conversationId: conversationIdToUse,
        role: 'assistant',
        content: '...', // Placeholder
        createdAt: new Date(),
      };
      const assistantMsgId = await db.messages.add(assistantMessagePlaceholder);
      setCurrentAssistantMessageId(assistantMsgId); // Track the ID of the streaming message
      setMessages(prev => [...prev, {...assistantMessagePlaceholder, id: assistantMsgId}]);


      for await (const chunk of ollamaApi.streamChat({ model: selectedModelName, messages: historyForApi })) {
        if (chunk.message?.content) {
          assistantResponseContent += chunk.message.content;
          setCurrentAssistantMessage(prev => prev + chunk.message!.content);
        }
        if (chunk.done) {
          if (chunk.done_reason === 'stop' || !chunk.done_reason) { // Handle normal completion
            // Stream finished
          } else {
             setError(`Stream finished with reason: ${chunk.done_reason}`);
          }
          break;
        }
      }

      // 4. Save complete assistant message
      if (assistantMsgId) {
        await db.messages.update(assistantMsgId, { content: assistantResponseContent, createdAt: new Date() });
      } else { // Should not happen if placeholder was added
        await db.messages.add({
            conversationId: conversationIdToUse,
            role: 'assistant',
            content: assistantResponseContent,
            createdAt: new Date(),
        });
      }
      // Refresh messages from DB to ensure consistency, especially IDs
      await loadMessages();
      setCurrentAssistantMessage('');
      setCurrentAssistantMessageId(null);

    } catch (err: any) {
      console.error('Failed to send message or stream response:', err);
      setError(err.error || err.message || 'Failed to get response from Ollama.');
      // Clean up potentially incomplete assistant message from UI if error occurred mid-stream
      if (currentAssistantMessageId) {
        setMessages(prev => prev.filter(msg => msg.id !== currentAssistantMessageId));
        await db.messages.delete(currentAssistantMessageId); // Also remove from DB
      }
      setCurrentAssistantMessage('');
      setCurrentAssistantMessageId(null);
    } finally {
      setIsLoading(false);
      onConversationUpdate(); // Refresh sidebar for updatedAt timestamp
    }
  };

  // TODO: Implement handleEditMessage
  const handleEditMessage = async (messageId: number, newContent: string) => {
    console.log("Editing message (not fully implemented):", messageId, newContent);
    // 1. Find the message to edit
    const messageToEdit = messages.find(m => m.id === messageId);
    if (!messageToEdit || messageToEdit.role !== 'user') {
      setError("Only user messages can be edited.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // 2. Delete subsequent messages from DB
      const messagesAfter = await db.messages
        .where('conversationId').equals(messageToEdit.conversationId)
        .and(msg => msg.createdAt > messageToEdit.createdAt)
        .toArray();

      const idsToDelete = messagesAfter.map(m => m.id!);
      if (idsToDelete.length > 0) {
        await db.messages.bulkDelete(idsToDelete);
      }

      // 3. Update the edited message's content in DB
      await db.messages.update(messageId, { content: newContent, createdAt: new Date() }); // Update timestamp to reflect edit

      // 4. Reload messages for the UI (up to the edited message)
      await loadMessages();
      // This will naturally truncate the UI. The next user message will continue from here.

      // 5. Optionally, auto-resend from this point if desired, or let user send next.
      // For now, we just update and let the user continue.
      // To resend, you'd construct history up to the edited message and call Ollama.

    } catch (err:any) {
      console.error("Error editing message:", err);
      setError(err.message || "Failed to edit message.");
    } finally {
      setIsLoading(false);
      onConversationUpdate();
    }
  };


  if (!selectedModelName && ollamaModels.length > 0) {
    // This check is more for initial state or if the selected model from App root is somehow empty
    // App.tsx should provide a valid selectedModelName if models are available
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 bg-gray-850">
        <p className="text-xl text-gray-400">Please select a model in the sidebar to start chatting.</p>
      </div>
    );
  }
   if (!ollamaModels || ollamaModels.length === 0) {
     return (
      <div className="flex-1 flex flex-col items-center justify-center p-4 bg-gray-850">
        <p className="text-xl text-gray-400">No Ollama models found. Please pull a model using Ollama CLI.</p>
      </div>
     );
   }


  return (
    <div className="flex-1 flex flex-col bg-gray-850 overflow-hidden">
      {/* Chat Header (Optional - e.g., show model name or conversation title) */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-gray-200">
          {conversation?.title || "New Conversation"}
        </h2>
        <p className="text-xs text-gray-400">Using model: {selectedModelName}</p>
      </div>

      {/* Messages Area */}
      <div className="flex-grow p-4 space-y-4 overflow-y-auto">
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} onEdit={handleEditMessage} />
        ))}
        {currentAssistantMessage && currentAssistantMessageId && (
          <MessageItem
            message={{
              id: currentAssistantMessageId,
              conversationId: conversation!.id!, // Should be set if streaming
              role: 'assistant',
              content: currentAssistantMessage,
              createdAt: new Date()
            }}
            isStreaming={true}
            onEdit={() => {}} // Assistants can't be edited this way
          />
        )}
        <div ref={messagesEndRef} /> {/* Anchor for scrolling */}
      </div>

      {/* Input Area */}
      {error && <p className="p-4 text-red-400 text-sm">{error}</p>}
      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center bg-gray-700 rounded-lg p-1">
          <textarea
            rows={Math.min(5, inputMessage.split('\n').length)} // Auto-expand up to 5 lines
            className="flex-grow p-2 bg-transparent text-gray-100 focus:outline-none resize-none"
            placeholder="Type your message..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            className={`ml-2 px-4 py-2 rounded-md text-white font-semibold transition duration-150
                        ${isLoading || !inputMessage.trim() || !selectedModelName
                          ? 'bg-gray-500 cursor-not-allowed'
                          : 'bg-blue-500 hover:bg-blue-600'}`}
            disabled={isLoading || !inputMessage.trim() || !selectedModelName}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
