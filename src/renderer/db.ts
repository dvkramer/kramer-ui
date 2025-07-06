import Dexie, { Table } from 'dexie';

export interface IConversation {
  id?: number; // Auto-incremented primary key
  title: string; // Auto-generated from first message
  model: string; // Ollama model name used for this conversation
  createdAt: Date;
  updatedAt: Date;
  // Add any other fields relevant to a conversation
}

export interface IMessage {
  id?: number; // Auto-incremented primary key
  conversationId: number; // Foreign key to IConversation
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
  // Add other fields like 'editedAt' if needed, or 'metadata' for options
}

class OllamaChatDB extends Dexie {
  public conversations!: Table<IConversation, number>;
  public messages!: Table<IMessage, number>;

  constructor() {
    super('OllamaChatDB'); // Database name
    this.version(1).stores({
      conversations: '++id, title, model, createdAt, updatedAt', // Primary key 'id' and indexes
      messages: '++id, conversationId, role, createdAt', // Primary key 'id' and indexes
    });

    // Future schema upgrades would go here, e.g.:
    // this.version(2).stores({
    //   conversations: '++id, title, model, createdAt, updatedAt, customField',
    //   messages: '++id, conversationId, role, content, createdAt, status',
    // }).upgrade(tx => {
    //   // Migration logic for existing data
    // });
  }
}

export const db = new OllamaChatDB();

// Example usage (can be removed or moved to actual service/component logic):
// async function testDB() {
//   try {
//     const newConversationId = await db.conversations.add({
//       title: 'My First Chat',
//       model: 'llama3',
//       createdAt: new Date(),
//       updatedAt: new Date(),
//     });
//     console.log('Added conversation with ID:', newConversationId);

//     await db.messages.add({
//       conversationId: newConversationId,
//       role: 'user',
//       content: 'Hello, world!',
//       createdAt: new Date(),
//     });
//     console.log('Added user message.');

//     const allConversations = await db.conversations.toArray();
//     console.log('All conversations:', allConversations);

//     const firstConvMessages = await db.messages.where('conversationId').equals(newConversationId).toArray();
//     console.log('Messages for first conversation:', firstConvMessages);

//   } catch (error) {
//     console.error('Dexie DB Error:', error);
//   }
// }

// testDB(); // Call for testing if needed
