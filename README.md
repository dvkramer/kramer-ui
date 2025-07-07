# Kramer UI for Ollama

A custom graphical user interface (GUI) built with `customtkinter` for interacting with Ollama, a local large language model server. This application provides a desktop client to chat with your Ollama models, manage conversations, and view responses in a streamlined interface.

## Features

* **Ollama Client Integration**: Connects to a local Ollama server (default: `http://127.0.0.1:11434`) to list and chat with models.
* **Model Selection**: Allows users to select from available Ollama models.
* **Chat Interface**: Provides a scrollable chat area for displaying conversation history.
* **Real-time Streaming**: Displays AI responses as they are generated.
* **Conversation Management**: Supports starting new chats and maintaining conversation history.
* **"Thinking" Content Display**: Parses and allows viewing of `think` blocks (content within `<think>` tags) from AI responses in a collapsible dropdown.
* **Responsive Layout**: Adjusts the chat area width based on the window size.
* **Status Bar**: Displays connection status and generation progress.

## Usage

To use Kramer UI for Ollama, download the executable file from the releases page and follow these steps:

1.  **Ensure Ollama is Running**: Make sure  Ollama is running and that you have models pulled.
2.  **Launch the Executable**: Double-click the executable file you've obtained.
3.  **Select a Model**: Once the application connects, choose an available model from the dropdown menu at the top right.
4.  **Start Chatting**: Type your message in the input box and press Enter or click the "Send" button.
5.  **New Chat**: Click "New Chat" to clear the current conversation and start fresh.
