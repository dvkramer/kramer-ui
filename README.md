# Kramer UI for Ollama

A custom graphical user interface (GUI) built with `customtkinter` for interacting with Ollama, a local large language model server. This application provides a desktop client to chat with your Ollama models, manage conversations, and view responses in a streamlined interface.

## Features

* **Ollama Client Integration**: Connects to a local Ollama server (default: `http://127.0.0.1:11434`) to list and chat with models.
* **Model Selection**: Allows users to select from available Ollama models.
* **Chat Interface**: Provides a scrollable chat area for displaying conversation history.
* **Real-time Streaming**: Displays AI responses as they are generated.
* **"Thinking" Content Display**: Parses and allows viewing of `think` blocks (content within `<think>` tags) from AI responses in a collapsible dropdown.
* **Responsive Layout**: Adjusts the chat area width based on the window size.

## Usage

Download the executable file (Kramer-UI.exe) from the releases page, then follow these steps:

1.  **Ensure Ollama is Running**: Make sure Ollama is running on your computer and that you have model(s) installed.
2.  **Launch the Executable**: Double-click the executable file.
3.  **Select a Model**: Once the application connects, choose an available model from the dropdown menu at the top right.
4.  **Start Chatting**: Type your message in the input box and press Enter or click the "Send" button.
