import sqlite3
import datetime

class DatabaseManager:
    def __init__(self, db_name="ollama_chat.db"):
        self.db_name = db_name
        # Establish a persistent connection, allowing it to be used across threads.
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row # Access columns by name
        self.cursor = self.conn.cursor()

    def close(self):
        """Closes the database connection when the application exits."""
        if self.conn:
            self.conn.close()

    def initialize_db(self):
        """
        Initializes the database by creating necessary tables if they don't exist.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            model TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL, -- 'user' or 'assistant'
            content TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
        """)
        self.conn.commit()
        print("Database initialized successfully.")

    def create_conversation(self, title: str, model: str = None) -> int:
        """
        Creates a new conversation.
        Args:
            title: The title of the conversation.
            model: The model used for this conversation.
        Returns:
            The ID of the newly created conversation.
        """
        now = datetime.datetime.now()
        self.cursor.execute("""
        INSERT INTO conversations (title, model, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """, (title, model, now, now))
        self.conn.commit()
        new_id = self.cursor.lastrowid
        if new_id is None or new_id == 0:
            raise sqlite3.OperationalError("Failed to retrieve a valid ID after inserting new conversation. lastrowid was None or 0.")
        return new_id

    def add_message(self, conversation_id: int, role: str, content: str) -> int:
        """
        Adds a new message to a conversation and updates the conversation's updated_at timestamp.
        Args:
            conversation_id: The ID of the conversation.
            role: The role of the message sender ('user' or 'assistant').
            content: The content of the message.
        Returns:
            The ID of the newly added message.
        """
        if conversation_id is None or not isinstance(conversation_id, int) or conversation_id <= 0:
            raise ValueError(f"Invalid conversation_id provided to add_message: {conversation_id}")
        now = datetime.datetime.now()
        # Add message
        self.cursor.execute("""
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, now))
        message_id = self.cursor.lastrowid

        # Update conversation's updated_at timestamp
        self.cursor.execute("""
        UPDATE conversations
        SET updated_at = ?
        WHERE id = ?
        """, (now, conversation_id))

        self.conn.commit()
        if message_id is None or message_id == 0:
             raise sqlite3.OperationalError("Failed to retrieve a valid ID after inserting new message. lastrowid was None or 0.")
        return message_id

    def get_conversations(self) -> list[sqlite3.Row]:
        """
        Retrieves all conversations, ordered by the most recently updated.
        Returns:
            A list of conversation rows.
        """
        self.cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
        return self.cursor.fetchall()

    def get_messages(self, conversation_id: int) -> list[sqlite3.Row]:
        """
        Retrieves all messages for a specific conversation, ordered by timestamp.
        Args:
            conversation_id: The ID of the conversation.
        Returns:
            A list of message rows.
        """
        self.cursor.execute("""
        SELECT * FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
        """, (conversation_id,))
        return self.cursor.fetchall()

    def delete_conversation(self, conversation_id: int):
        """
        Deletes a conversation and all its associated messages.
        Args:
            conversation_id: The ID of the conversation to delete.
        """
        self.cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        # Messages are deleted automatically due to ON DELETE CASCADE
        self.conn.commit()

    def delete_messages_from(self, conversation_id: int, message_id: int):
        """
        Deletes a specific message and all subsequent messages in a conversation.
        This is used for conversation branching when a message is edited.
        Args:
            conversation_id: The ID of the conversation.
            message_id: The ID of the message from which to start deleting.
                       This message itself will also be deleted.
        """
        # First, get the timestamp of the message to be deleted
        self.cursor.execute("SELECT timestamp FROM messages WHERE id = ?", (message_id,))
        result = self.cursor.fetchone()
        if not result:
            print(f"Message with id {message_id} not found.")
            return

        message_timestamp = result['timestamp']

        # Delete the target message and all messages after it in the same conversation
        self.cursor.execute("""
        DELETE FROM messages
        WHERE conversation_id = ? AND timestamp >= ?
        """, (conversation_id, message_timestamp))

        # Update conversation's updated_at timestamp to the timestamp of the last message
        # or current time if no messages are left
        self.cursor.execute("""
        UPDATE conversations
        SET updated_at = (
            SELECT COALESCE(MAX(timestamp), ?)
            FROM messages
            WHERE conversation_id = ?
        )
        WHERE id = ?
        """, (datetime.datetime.now(), conversation_id, conversation_id))

        self.conn.commit()

    def update_conversation_model(self, conversation_id: int, model: str):
        """
        Updates the model for a given conversation.
        Args:
            conversation_id: The ID of the conversation.
            model: The new model name.
        """
        now = datetime.datetime.now()
        self.cursor.execute("""
        UPDATE conversations
        SET model = ?, updated_at = ?
        WHERE id = ?
        """, (model, now, conversation_id))
        self.conn.commit()

    def update_message_content(self, message_id: int, new_content: str):
        """
        Updates the content of a specific message.
        This is typically called before `delete_messages_from` if an existing message is being edited.
        Args:
            message_id: The ID of the message to update.
            new_content: The new content for the message.
        """
        now = datetime.datetime.now() # Consider if timestamp should update
        self.cursor.execute("""
        UPDATE messages
        SET content = ?, timestamp = ?
        WHERE id = ?
        """, (new_content, now, message_id))

        # Also update the conversation's updated_at timestamp
        self.cursor.execute("""
        UPDATE conversations
        SET updated_at = ?
        WHERE id = (SELECT conversation_id FROM messages WHERE id = ?)
        """, (now, message_id))
        self.conn.commit()


if __name__ == '__main__':
    # Test the DatabaseManager
    DB_FILE = "test_ollama_chat.db"
    # Clean up previous test database if it exists
    import os
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    db = DatabaseManager(db_name=DB_FILE)
    db.initialize_db()

    print("\nTesting DatabaseManager...")

    # Create conversations
    conv1_id = db.create_conversation(title="First Chat", model="llama3")
    conv2_id = db.create_conversation(title="Second Chat", model="phi3")
    print(f"Created conversations with IDs: {conv1_id}, {conv2_id}")

    # Add messages
    msg1_id = db.add_message(conv1_id, "user", "Hello Llama3!")
    msg2_id = db.add_message(conv1_id, "assistant", "Hello User! How can I help?")
    msg3_id = db.add_message(conv2_id, "user", "Hi Phi3, tell me a joke.")
    print(f"Added messages with IDs: {msg1_id}, {msg2_id}, {msg3_id}")

    # Get conversations
    print("\nCurrent conversations:")
    conversations = db.get_conversations()
    for conv in conversations:
        print(f"  ID: {conv['id']}, Title: {conv['title']}, Model: {conv['model']}, Updated: {conv['updated_at']}")

    # Get messages for conv1
    print(f"\nMessages for conversation {conv1_id} ('{conversations[1]['title']}'):") # This will fail if conv2 was updated more recently
    messages_conv1 = db.get_messages(conv1_id)
    for msg in messages_conv1:
        print(f"  ID: {msg['id']}, Role: {msg['role']}, Content: '{msg['content']}', Time: {msg['timestamp']}")

    # Update conversation model
    db.update_conversation_model(conv1_id, "llama3-instruct")
    print(f"\nUpdated model for conversation {conv1_id}.")
    # Need to refetch conversations to get the correct updated_at time
    updated_conv1 = None
    for c in db.get_conversations():
        if c['id'] == conv1_id:
            updated_conv1 = c
            break
    if updated_conv1:
        print(f"  New model: {updated_conv1['model']}, Updated: {updated_conv1['updated_at']}")


    # Test message editing (update content then delete subsequent)
    # Add a few more messages to conv1
    msg_before_edit_id = db.add_message(conv1_id, "user", "What is the capital of France?")
    msg_to_be_deleted1_id = db.add_message(conv1_id, "assistant", "Paris, of course!")
    msg_to_be_deleted2_id = db.add_message(conv1_id, "user", "Thanks!")

    print(f"\nMessages for conversation {conv1_id} before editing message ID {msg_before_edit_id}:")
    messages_before_edit = db.get_messages(conv1_id)
    for msg in messages_before_edit:
        print(f"  ID: {msg['id']}, Content: '{msg['content']}'")

    # Edit message msg_before_edit_id
    print(f"\nEditing message ID {msg_before_edit_id} and deleting subsequent messages...")
    db.update_message_content(msg_before_edit_id, "What is the capital of Spain?")
    db.delete_messages_from(conv1_id, msg_to_be_deleted1_id)


    print(f"\nMessages for conversation {conv1_id} after editing message ID {msg_before_edit_id}:")
    messages_after_edit = db.get_messages(conv1_id)
    for msg in messages_after_edit:
        print(f"  ID: {msg['id']}, Role: {msg['role']}, Content: '{msg['content']}'")

    # Verify that only messages up to and including the *newly content updated* msg_before_edit_id remain.
    assert len(messages_after_edit) == 3 # msg1, msg2, msg_before_edit_id (updated)
    assert messages_after_edit[-1]['id'] == msg_before_edit_id
    assert messages_after_edit[-1]['content'] == "What is the capital of Spain?"


    # Delete a conversation
    print(f"\nDeleting conversation {conv2_id}...")
    db.delete_conversation(conv2_id)
    remaining_conversations = db.get_conversations()
    print("Remaining conversations:")
    for conv in remaining_conversations:
        print(f"  ID: {conv['id']}, Title: {conv['title']}")
    assert len(remaining_conversations) == 1
    assert remaining_conversations[0]['id'] == conv1_id

    # Test getting messages from a deleted conversation (should be empty)
    messages_deleted_conv = db.get_messages(conv2_id)
    print(f"\nMessages for deleted conversation {conv2_id}: {messages_deleted_conv}")
    assert len(messages_deleted_conv) == 0

    print("\nDatabaseManager tests completed.")
    db.close() # Close the persistent connection

    # Clean up test database
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    print(f"Test database {DB_FILE} removed.")
