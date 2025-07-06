# Ollama Windows Desktop Chat Application

This is a native Windows desktop application built with Python and Tkinter that provides a graphical user interface (GUI) for interacting with Ollama models. It allows users to chat with various Ollama models, manage conversations, and select models dynamically.

## Features

*   **Chat Interface:** Real-time, streaming chat with Ollama models.
*   **Model Selection:** Dropdown to select any available Ollama model for the current conversation. Model choice persists per conversation.
*   **Conversation Management:**
    *   List of conversations displayed in a sidebar.
    *   Conversations are automatically titled based on the first user message.
    *   Ability to start new conversations.
    *   Ability to delete existing conversations (including all messages).
*   **Message Editing:**
    *   Edit your previously sent messages.
    *   The conversation branches from the edited point; subsequent messages from the original branch are deleted.
*   **Local Storage:** Conversations and messages are saved locally in an SQLite database (`data/ollama_chat_history.db`).
*   **Ollama Integration:**
    *   Connects to a running Ollama instance (default: `http://localhost:11434`).
    *   Dynamically loads the list of available models from Ollama.
    *   Connection status indicator.
*   **Standalone Executable:** Can be packaged into a Windows executable using PyInstaller.

## Technical Stack

*   **Python:** 3.9+
*   **GUI Framework:** Tkinter (via Python's standard library `tkinter.ttk`)
*   **Database:** SQLite3 (via Python's standard library `sqlite3`)
*   **HTTP Requests:** `requests` library (for Ollama API communication)
*   **Threading:** For non-blocking UI operations (streaming responses, status checks).
*   **Packaging:** PyInstaller (for creating the `.exe`)

## Prerequisites

*   **Python 3.9 or higher:** Make sure Python is installed and added to your system's PATH.
*   **Ollama:** An Ollama instance must be running and accessible. By default, the application connects to `http://localhost:11434`. Download and install Ollama from [ollama.com](https://ollama.com/).
*   **Ollama Models:** You need to have at least one model pulled in Ollama (e.g., `ollama pull phi3`).

## Setup and Running the Application from Source

1.  **Clone the repository (if applicable) or download the source files.**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Navigate to the project root directory (where `requirements.txt` is located) and run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

## Building the Executable (.exe)

To create a standalone Windows executable:

1.  **Ensure PyInstaller is installed:**
    If you haven't installed it via `requirements.txt`, or for global use:
    ```bash
    pip install pyinstaller
    ```

2.  **Navigate to the project root directory.**

3.  **Run PyInstaller:**
    *   For a **folder-based distribution** (creates a folder with the `.exe` and all dependencies - recommended for easier debugging):
        ```bash
        pyinstaller --name OllamaChatApp --windowed --onedir main.py
        ```
    *   For a **single-file executable** (creates one `.exe` file, may have slower startup):
        ```bash
        pyinstaller --name OllamaChatApp --windowed --onefile main.py
        ```

4.  **Locate the Executable:**
    The bundled application will be in the `dist/OllamaChatApp` directory (e.g., `dist/OllamaChatApp/OllamaChatApp.exe`).

5.  **Important for Developers (Git):**
    If you are using Git, add the following lines to your `.gitignore` file to prevent committing PyInstaller's generated files:
    ```gitignore
    # PyInstaller files
    /build/
    /dist/
    *.spec
    ```

## Project Structure

```
ollama_windows_app/
├── main.py                 # Main application script, integrates all modules
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── data/                   # Directory for database file (created automatically)
│   └── ollama_chat_history.db # SQLite database (created automatically)
├── ollama_api/             # Module for Ollama API interactions
│   ├── __init__.py
│   └── ollama_client.py    # OllamaClient class
├── database/               # Module for database operations
│   ├── __init__.py
│   └── db_manager.py       # DatabaseManager class
└── ui/                     # Module for Tkinter UI
    ├── __init__.py
    └── app_ui.py           # AppUI class
```

## Notes

*   The application creates a `data` subdirectory in its root for the SQLite database file (`ollama_chat_history.db`).
*   Error handling is implemented for database operations, API calls, and general application flow. Status messages and errors are typically shown in the status bar at the bottom of the application window or via message boxes.
```
