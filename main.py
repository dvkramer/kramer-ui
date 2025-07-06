import tkinter as tk
from database.db_manager import DatabaseManager
from ollama_api.ollama_client import OllamaClient
from ui.app_ui import AppUI
import os

# Define the name for the SQLite database file
# Store it in a user-specific directory for better practice, e.g. appdata
# For simplicity in this project, we'll place it alongside the application or in a 'data' subfolder.
# Check if a 'data' directory exists, if not create it.
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")
    except OSError as e:
        print(f"Error creating directory {DATA_DIR}: {e}. Using current directory for DB.")
        DATA_DIR = "." # Fallback to current directory

DB_NAME = os.path.join(DATA_DIR, "ollama_chat_history.db")
OLLAMA_BASE_URL = "http://localhost:11434" # Default Ollama URL

def main():
    # Initialize DatabaseManager
    # This will also create the DB file and tables if they don't exist.
    db_manager = DatabaseManager(db_name=DB_NAME)
    try:
        db_manager.initialize_db() # Ensures tables are created
        print(f"Database initialized at {DB_NAME}")
    except Exception as e:
        print(f"Critical error initializing database: {e}")
        # Optionally, show a GUI error message here if Tk root can be created briefly
        # For now, exiting if DB can't be set up.
        root = tk.Tk()
        root.withdraw() # Hide the main window
        tk.messagebox.showerror("Database Error", f"Could not initialize database: {e}\nThe application will now exit.")
        root.destroy()
        return

    # Initialize OllamaClient
    ollama_client = OllamaClient(base_url=OLLAMA_BASE_URL)

    # Initial connection check to Ollama (optional, UI also does periodic checks)
    # This is more for an early warning before UI fully loads.
    print("Checking initial connection to Ollama server...")
    connected, message = ollama_client.check_connection()
    if not connected:
        print(f"Warning: Could not connect to Ollama server at {OLLAMA_BASE_URL}. {message}")
        # UI will show this status, but we can also inform user early via console or a popup
        # For now, let UI handle displaying this. We could use a tk.messagebox.showwarning here too.

    # Initialize and run the Tkinter UI
    root = tk.Tk()
    app_ui = AppUI(root, db_manager, ollama_client)

    # Set a minimum size for the window
    root.minsize(600, 400)

    # Handle window close event
    def on_closing():
        print("Closing application...")
        # Potentially stop any active Ollama streams
        if hasattr(ollama_client, 'stop_current_stream') and callable(ollama_client.stop_current_stream):
            print("Attempting to stop any active Ollama streams...")
            ollama_client.stop_current_stream()
            # Give a brief moment for stream to acknowledge stop if it's in a tight loop.
            # This is a bit of a guess; robust stream termination needs careful handling.
            # root.after(500, root.destroy) # Wait 500ms then destroy
            # For now, direct destroy. UI threads are daemonic.

        # DB connection is managed by context manager ('with self') in db_manager,
        # so explicit close on app exit isn't strictly necessary unless operations are pending.

        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    print("Starting UI main loop...")
    root.mainloop()
    print("Application closed.")

if __name__ == "__main__":
    # Add basic error handling for the main execution
    try:
        main()
    except Exception as e:
        # Log critical errors that weren't caught elsewhere
        print(f"An unhandled critical error occurred: {e}")
        # Show a simple Tkinter error box if possible
        try:
            error_root = tk.Tk()
            error_root.withdraw()
            tk.messagebox.showerror("Critical Error", f"An unhandled critical error occurred: {e}\nPlease report this issue.\nThe application will now exit.")
            error_root.destroy()
        except tk.TclError: # If Tkinter itself fails
            pass # Just print to console then
        # Ensure exit if main() fails catastrophically
        import sys
        sys.exit(1)
