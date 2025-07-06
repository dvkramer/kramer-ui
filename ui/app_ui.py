import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import datetime
import threading
import queue # For thread-safe UI updates

# Assuming db_manager.py and ollama_client.py are in sibling directories
# For direct execution of this file for testing, Python path might need adjustment
# However, when run from main.py, imports should work if structured as packages.
# from database.db_manager import DatabaseManager # Will be used when integrated
# from ollama_api.ollama_client import OllamaClient # Will be used when integrated

import sv_ttk # For dark theme

class AppUI:
    def __init__(self, root, db_manager, ollama_client):
        self.root = root
        self.db_manager = db_manager
        self.ollama_client = ollama_client

        self.root.title("Ollama Chat Client")
        self.root.geometry("1000x700")

        # Apply sv-ttk theme
        sv_ttk.set_theme("dark") # Or "light"

        self.current_conversation_id = None
        self.current_model = tk.StringVar()
        self.available_models = []
        self.ui_update_queue = queue.Queue() # Queue for thread-safe UI updates

        self._setup_styles() # Custom styles might override or complement sv_ttk
        self._setup_ui()

        self.load_conversations()
        self.load_models_into_dropdown()
        self.check_ollama_status_periodically()

        # Start polling the queue for UI updates
        self.root.after(100, self.process_ui_queue)

    def process_ui_queue(self):
        """Process tasks from the UI update queue."""
        try:
            while True: # Process all pending tasks
                task, args, kwargs = self.ui_update_queue.get_nowait()
                task(*args, **kwargs)
        except queue.Empty:
            pass # No tasks in queue
        finally:
            self.root.after(100, self.process_ui_queue) # Poll again

    def queue_ui_update(self, callable_task, *args, **kwargs):
        """Safely schedules a UI update from any thread."""
        self.ui_update_queue.put((callable_task, args, kwargs))

    def _setup_styles(self):
        self.style = ttk.Style()
        # self.style.theme_use('clam') # sv_ttk handles the base theme

        # Define custom styles that complement the dark theme
        # Use lighter colors for text on a dark background
        self.style.configure("User.TLabel", foreground="#70AEEF", padding=(0, 2, 0, 2)) # Light Blue
        self.style.configure("Assistant.TLabel", foreground="#A0EFA0", padding=(0, 2, 0, 2)) # Light Green
        self.style.configure("Timestamp.TLabel", foreground="grey", font=('TkDefaultFont', 7), padding=(0,0,0,2))
        self.style.configure("Error.TLabel", foreground="#FF8080") # Light Red
        self.style.configure("Status.TLabel", padding=5)

        # Selected.TFrame might not be needed if sv_ttk handles listbox selection well,
        # or it might need a dark-theme appropriate color.
        # For now, let's comment it out or use a color from sv-ttk if available.
        # self.style.configure("Selected.TFrame", background="#4c4c4c") # Example dark selection

    def _setup_ui(self):
        # Main PanedWindow for resizable sidebar
        self.main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(expand=True, fill=tk.BOTH)

        # Left: Conversations Sidebar
        self.sidebar_frame = ttk.Frame(self.main_paned_window, width=250)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.main_paned_window.add(self.sidebar_frame, weight=1) # Initial weight

        # --- Sidebar Widgets ---
        self.new_conv_button = ttk.Button(self.sidebar_frame, text="New Conversation", command=self.start_new_conversation)
        self.new_conv_button.pack(pady=5, padx=5, fill=tk.X)

        self.conversations_listbox_frame = ttk.Frame(self.sidebar_frame)
        self.conversations_listbox_frame.pack(expand=True, fill=tk.BOTH, padx=5)

        self.conv_list_scrollbar = ttk.Scrollbar(self.conversations_listbox_frame, orient=tk.VERTICAL)
        self.conversations_listbox = tk.Listbox(
            self.conversations_listbox_frame,
            yscrollcommand=self.conv_list_scrollbar.set,
            exportselection=False,
            activestyle='none' # To manually control selection appearance
        )
        self.conv_list_scrollbar.config(command=self.conversations_listbox.yview)
        self.conv_list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.conversations_listbox.pack(expand=True, fill=tk.BOTH)
        self.conversations_listbox.bind("<<ListboxSelect>>", self.on_conversation_select)

        # Context menu for conversations list
        self.conv_context_menu = tk.Menu(self.root, tearoff=0)
        self.conv_context_menu.add_command(label="Delete Conversation", command=self.delete_selected_conversation)
        self.conversations_listbox.bind("<Button-3>", self.show_conv_context_menu)


        # Right: Chat Area
        self.chat_area_frame = ttk.Frame(self.main_paned_window)
        self.chat_area_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.main_paned_window.add(self.chat_area_frame, weight=4) # Initial weight

        # --- Chat Area Widgets ---
        # Model Selector and Refresh Button
        self.model_frame = ttk.Frame(self.chat_area_frame)
        self.model_frame.pack(fill=tk.X, padx=5, pady=(5,0))

        ttk.Label(self.model_frame, text="Model:").pack(side=tk.LEFT, padx=(0,5))
        self.model_selector = ttk.Combobox(self.model_frame, textvariable=self.current_model, state="readonly", width=30)
        self.model_selector.pack(side=tk.LEFT, padx=(0,5))
        self.model_selector.bind("<<ComboboxSelected>>", self.on_model_selected_for_conversation)

        self.refresh_models_button = ttk.Button(self.model_frame, text="Refresh Models", command=self.load_models_into_dropdown)
        self.refresh_models_button.pack(side=tk.LEFT, padx=(5,0))

        # Chat Messages Display
        # The canvas background should ideally be themed by sv_ttk.
        # If not, we might need to fetch a color from the style.
        # For now, let sv_ttk handle it or it will use its default.
        self.chat_messages_canvas = tk.Canvas(self.chat_area_frame, borderwidth=0)
        # Example of trying to get a theme color:
        # bg_color = self.style.lookup('TFrame', 'background') # Get default frame background
        # self.chat_messages_canvas.configure(background=bg_color)

        self.chat_messages_frame = ttk.Frame(self.chat_messages_canvas, style="Messages.TFrame")
        self.chat_v_scrollbar = ttk.Scrollbar(self.chat_area_frame, orient="vertical", command=self.chat_messages_canvas.yview)
        self.chat_messages_canvas.configure(yscrollcommand=self.chat_v_scrollbar.set)

        self.chat_v_scrollbar.pack(side="right", fill="y")
        self.chat_messages_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.chat_messages_canvas.create_window((0,0), window=self.chat_messages_frame, anchor="nw", tags="self.chat_messages_frame")

        self.chat_messages_frame.bind("<Configure>", self._on_chat_frame_configure)
        self.chat_messages_canvas.bind_all("<MouseWheel>", self._on_mousewheel) # For scrolling with mouse

        # Message context menu
        self.message_context_menu = tk.Menu(self.root, tearoff=0)
        self.message_context_menu.add_command(label="Edit Message", command=self.edit_selected_message)
        # Add "Copy" later if needed

        # User Input Area
        self.input_frame = ttk.Frame(self.chat_area_frame, padding=(5,5,5,10))
        self.input_frame.pack(fill=tk.X)

        self.message_input = scrolledtext.ScrolledText(self.input_frame, height=3, relief=tk.SOLID, borderwidth=1)
        self.message_input.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        self.message_input.bind("<Return>", self.send_message_on_enter) # Shift+Enter for newline
        self.message_input.bind("<Shift-Return>", self.insert_newline_in_input)

        # Apply dark theme to ScrolledText's internal Text widget
        try:
            # These colors should ideally be from the theme, e.g. self.style.lookup('TEntry', 'fieldbackground') or similar
            st_bg_color = "#2B2B2B" # Example dark background
            st_fg_color = "#D3D3D3" # Example light foreground
            st_insert_color = self.style.lookup('TEntry', 'insertcolor', default=st_fg_color) # Get themed cursor color if possible

            self.message_input.configure(
                background=st_bg_color,
                foreground=st_fg_color,
                insertbackground=st_insert_color,
                relief=tk.FLAT # Make relief flatter to match modern themes
            )
            # Configure selection colors if needed (though sv-ttk might handle these)
            # self.message_input.tag_configure("sel", background="...", foreground="...")
        except tk.TclError as e:
            print(f"Warning: Could not apply all dark theme styles to ScrolledText input: {e}")


        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)

        # Status Bar
        self.status_bar = ttk.Label(self.root, text="Status: Initializing...", anchor=tk.W, style="Status.TLabel")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_chat_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.chat_messages_canvas.configure(scrollregion=self.chat_messages_canvas.bbox("all"))

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling for the chat canvas."""
        # Determine which canvas/widget should scroll. For now, assume chat_messages_canvas if mouse is over it or its children.
        # A more robust solution would check event.widget.
        if self.chat_messages_canvas.winfo_containing(event.x_root, event.y_root) == self.chat_messages_canvas:
            # For Windows, event.delta is usually +/- 120. For Linux/macOS, it might be different.
            scroll_val = -1 * (event.delta // 120) # For Windows
            if event.num == 5: # Linux scroll down
                scroll_val = 1
            elif event.num == 4: # Linux scroll up
                scroll_val = -1
            self.chat_messages_canvas.yview_scroll(scroll_val, "units")


    def _scroll_chat_to_bottom(self):
        self.chat_messages_canvas.update_idletasks() # Ensure canvas size is updated
        self.chat_messages_canvas.yview_moveto(1.0)

    def _add_message_to_display(self, message_id, role, content, timestamp, is_streaming=False):
        """Adds a single message to the chat display area."""
        msg_frame = ttk.Frame(self.chat_messages_frame, padding=(5,2))
        msg_frame.pack(fill=tk.X, anchor=tk.NW)

        # Store message_id with the frame for later reference (e.g., editing)
        msg_frame.message_id = message_id
        msg_frame.role = role # Store role for context menu logic

        # Role and Content Label (combined for easier layout)
        # Using Text widget for selectable text
        text_content = tk.Text(msg_frame, wrap=tk.WORD, height=1, borderwidth=0, relief="flat", padx=0, pady=0)

        # Dark theme adjustments for tk.Text widget
        # Ideally, these colors would be derived from the sv_ttk theme if possible.
        text_bg_color = "#2B2B2B"  # Example dark background for text areas
        text_fg_color = "#D3D3D3"  # Example light foreground for text

        text_content.config(background=text_bg_color, insertbackground=text_fg_color) # Set background & cursor color

        # Use theme-appropriate colors for roles (already defined in _setup_styles for Labels, reuse for text)
        user_role_color = self.style.lookup("User.TLabel", "foreground")
        assistant_role_color = self.style.lookup("Assistant.TLabel", "foreground")

        text_content.tag_config("role_user", foreground=user_role_color, font=('TkDefaultFont', 10, 'bold'))
        text_content.tag_config("role_assistant", foreground=assistant_role_color, font=('TkDefaultFont', 10, 'bold'))
        text_content.tag_config("content", foreground=text_fg_color, font=('TkDefaultFont', 10))

        text_content.insert(tk.END, f"{role.capitalize()}: ", f"role_{role.lower()}")
        text_content.insert(tk.END, content, "content")

        text_content.pack(fill=tk.X, anchor=tk.NW)
        text_content.configure(state="disabled") # Make it read-only
        text_content.bind("<Button-3>", lambda event, mid=message_id, m_frame=msg_frame: self.show_message_context_menu(event, mid, m_frame))

        # Auto-adjust height of Text widget
        text_content.update_idletasks()
        lines = text_content.count("1.0", "end-1c", "displaylines")[0]
        text_content.config(height=lines if lines > 0 else 1)

        # Timestamp Label
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, datetime.datetime) else str(timestamp)
        ts_label = ttk.Label(msg_frame, text=ts_str, style="Timestamp.TLabel")
        ts_label.pack(anchor=tk.NW)

        self._on_chat_frame_configure() # Update scrollregion
        if not is_streaming: # Only scroll to bottom for non-streaming or final stream message
             self._scroll_chat_to_bottom()

        return msg_frame # Return the frame in case we need to update it (e.g., streaming)

    def _update_streaming_message_display(self, assistant_msg_frame, new_content_chunk):
        """Appends a chunk to the assistant's message in the display."""
        if not assistant_msg_frame or not assistant_msg_frame.winfo_exists(): # Check if frame still exists
            return

        text_widget = None
        for widget in assistant_msg_frame.winfo_children():
            if isinstance(widget, tk.Text):
                text_widget = widget
                break

        if text_widget:
            text_widget.configure(state="normal")
            text_widget.insert(tk.END, new_content_chunk, "content")
            text_widget.configure(state="disabled")

            # Auto-adjust height
            text_widget.update_idletasks()
            lines = text_widget.count("1.0", "end-1c", "displaylines")[0]
            text_widget.config(height=lines if lines > 0 else 1)

            self._scroll_chat_to_bottom()
            self._on_chat_frame_configure()

    def _clear_chat_display(self):
        for widget in self.chat_messages_frame.winfo_children():
            widget.destroy()
        self._on_chat_frame_configure()

    def show_conv_context_menu(self, event):
        selection_indices = self.conversations_listbox.curselection()
        if not selection_indices:
            return
        self.conv_context_menu.conv_id_to_delete = self.conversations_listbox.get(selection_indices[0])[0] # Get ID
        self.conv_context_menu.post(event.x_root, event.y_root)

    def show_message_context_menu(self, event, message_id, msg_frame):
        # Only allow editing user messages for now, or if assistant message editing is a feature
        if msg_frame.role == "user": # Or check based on requirements
            self.message_context_menu.message_id_to_edit = message_id
            self.message_context_menu.message_frame_to_edit = msg_frame
            self.message_context_menu.post(event.x_root, event.y_root)
        # Could also add "Copy" for any message type

    def load_conversations(self):
        """Loads conversation list from DB into the listbox."""
        self.conversations_listbox.delete(0, tk.END)
        try:
            conversations = self.db_manager.get_conversations()
            for conv in conversations:
                # Store (id, title) but display only title
                # Using a simple tuple for now. Could be object later.
                title_display = f"{conv['title']}"
                if len(title_display) > 30: # Truncate for display
                    title_display = title_display[:27] + "..."
                self.conversations_listbox.insert(tk.END, (conv['id'], title_display, conv['model']))
        except Exception as e:
            self.update_status_bar(f"Error loading conversations: {e}", is_error=True)
            print(f"Error loading conversations: {e}")

    def on_conversation_select(self, event=None):
        """Handles selection of a conversation from the list."""
        selection_indices = self.conversations_listbox.curselection()
        if not selection_indices:
            if self.current_conversation_id is not None: # Deselection, clear chat
                self._clear_chat_display()
                self.current_conversation_id = None
                self.current_model.set("")
                self.update_status_bar("No conversation selected.")
            return

        selected_index = selection_indices[0]
        conv_data = self.conversations_listbox.get(selected_index)
        conv_id, _, conv_model_name = conv_data # id, title_display, model_name

        if self.current_conversation_id == conv_id:
            return # Already selected

        self.current_conversation_id = conv_id
        self.set_current_model_for_ui(conv_model_name or "") # Set model in dropdown

        self._clear_chat_display()
        try:
            messages = self.db_manager.get_messages(self.current_conversation_id)
            for msg in messages:
                self._add_message_to_display(msg['id'], msg['role'], msg['content'], msg['timestamp'])
            # Use the title_display from listbox data for status bar
            self.update_status_bar(f"Loaded conversation: {conv_data[1]}")
        except Exception as e:
            self.update_status_bar(f"Error loading messages: {e}", is_error=True)
            print(f"Error loading messages for conv {self.current_conversation_id}: {e}")
        self._scroll_chat_to_bottom()

    def set_current_model_for_ui(self, model_name: str):
        """Sets the model in the UI dropdown. If model_name is not in list, adds it."""
        if model_name and model_name not in self.available_models:
            self.available_models.append(model_name)
            self.model_selector['values'] = self.available_models

        if model_name in self.available_models:
            self.current_model.set(model_name)
        elif self.available_models: # Default to first if given model not found
            self.current_model.set(self.available_models[0])
        else: # No models available at all
            self.current_model.set("")


    def start_new_conversation(self):
        self.current_conversation_id = None # Indicate it's a new conversation
        self._clear_chat_display()
        self.conversations_listbox.selection_clear(0, tk.END) # Deselect in listbox
        # Do not reset model dropdown, let user pick or use last selected one.
        # If no model selected, prompt or use a default.
        if not self.current_model.get() and self.available_models:
            self.current_model.set(self.available_models[0])

        self.update_status_bar("New conversation started. Type a message.")
        self.message_input.focus_set()

    def delete_selected_conversation(self):
        conv_id_to_delete = getattr(self.conv_context_menu, 'conv_id_to_delete', None)
        if not conv_id_to_delete:
            # This might happen if context menu shown then listbox selection changes.
            # Fallback to current selection if any.
            selection_indices = self.conversations_listbox.curselection()
            if not selection_indices:
                messagebox.showwarning("Delete Conversation", "No conversation selected to delete.")
                return
            conv_id_to_delete = self.conversations_listbox.get(selection_indices[0])[0]

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this conversation? This cannot be undone."):
            return

        try:
            self.db_manager.delete_conversation(conv_id_to_delete)
            self.load_conversations() # Refresh list
            if self.current_conversation_id == conv_id_to_delete:
                self.start_new_conversation() # Clear chat area if deleted conv was active
            self.update_status_bar(f"Conversation deleted.", is_error=False)
        except Exception as e:
            self.update_status_bar(f"Error deleting conversation: {e}", is_error=True)
            messagebox.showerror("Delete Error", f"Could not delete conversation: {e}")


    def load_models_into_dropdown(self, show_status=True):
        if show_status: self.update_status_bar("Loading models...")
        try:
            response = self.ollama_client.list_models()
            if response and "models" in response:
                self.available_models = sorted([model['name'] for model in response['models']])
                self.model_selector['values'] = self.available_models

                # Preserve current selection if possible, or set to first
                current_selection = self.current_model.get()
                if current_selection and current_selection in self.available_models:
                    self.current_model.set(current_selection)
                elif self.available_models:
                    self.current_model.set(self.available_models[0])
                else:
                    self.current_model.set("") # No models found
                if show_status: self.update_status_bar("Models loaded.", False)
            else:
                self.available_models = []
                self.model_selector['values'] = []
                self.current_model.set("")
                if show_status: self.update_status_bar("No models found or error fetching models.", True)
        except Exception as e:
            self.available_models = []
            self.model_selector['values'] = []
            self.current_model.set("")
            if show_status: self.update_status_bar(f"Error loading models: {e}", is_error=True)
            print(f"Error loading models: {e}")

    def on_model_selected_for_conversation(self, event=None):
        """When user changes model in dropdown, update DB if a conversation is active."""
        selected_model = self.current_model.get()
        if self.current_conversation_id and selected_model:
            try:
                self.db_manager.update_conversation_model(self.current_conversation_id, selected_model)
                self.update_status_bar(f"Model for current conversation set to {selected_model}.")
                # Refresh conversation list to show updated model potentially
                self.load_conversations()
                # Re-select the current conversation in the listbox
                for i in range(self.conversations_listbox.size()):
                    if self.conversations_listbox.get(i)[0] == self.current_conversation_id:
                        self.conversations_listbox.selection_set(i)
                        break
            except Exception as e:
                self.update_status_bar(f"Error updating model for conversation: {e}", is_error=True)
                messagebox.showerror("Model Update Error", f"Could not save model selection: {e}")

    def send_message_on_enter(self, event):
        # Send on Enter, allow Shift+Enter for newline
        if event.state & 0x0001: # Shift key pressed
            return # Let the default Shift+Enter behavior for ScrolledText insert newline
        self.send_message()
        return "break" # Prevents default Enter key behavior (which might add a newline)

    def insert_newline_in_input(self, event):
        # This is implicitly handled by ScrolledText if not caught by send_message_on_enter
        pass

    def send_message(self):
        user_content = self.message_input.get("1.0", tk.END).strip()
        if not user_content:
            return

        selected_model = self.current_model.get()
        if not selected_model:
            messagebox.showerror("No Model Selected", "Please select a model from the dropdown.")
            return

        # Disable input and send button during processing
        self.message_input.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.update_status_bar(f"Sending to {selected_model}...")

        temp_conv_id = self.current_conversation_id

        # If it's a new conversation, create it first
        if temp_conv_id is None:
            title = user_content.split('\n')[0][:50] # First 50 chars of first line as title
            try:
                temp_conv_id = self.db_manager.create_conversation(title=title, model=selected_model)
                if not isinstance(temp_conv_id, int) or temp_conv_id <= 0:
                    raise Exception(f"Failed to create a valid conversation ID: {temp_conv_id}")
                self.current_conversation_id = temp_conv_id # Set it as current
                self.load_conversations() # Refresh list
                # Auto-select the new conversation in the listbox
                for i in range(self.conversations_listbox.size()):
                    if self.conversations_listbox.get(i)[0] == temp_conv_id:
                        self.conversations_listbox.selection_set(i)
                        self.conversations_listbox.see(i) # Ensure it's visible
                        break
            except Exception as e:
                self.update_status_bar(f"Error creating new conversation: {e}", is_error=True)
                messagebox.showerror("DB Error", f"Could not create new conversation: {type(e).__name__}: {e}")
                self._enable_input()
                return

        # Before adding user message, ensure temp_conv_id is valid
        if not isinstance(temp_conv_id, int) or temp_conv_id <= 0:
            self.update_status_bar("Cannot save message: Invalid conversation state.", is_error=True)
            messagebox.showerror("DB Error", "Cannot save message due to an invalid conversation state. Try starting a new conversation.")
            self._enable_input()
            return

        # Add user message to DB and display
        try:
            user_msg_id = self.db_manager.add_message(temp_conv_id, "user", user_content)
            if not isinstance(user_msg_id, int) or user_msg_id <= 0:
                 raise Exception(f"Failed to save message, received invalid message ID: {user_msg_id}")
            self._add_message_to_display(user_msg_id, "user", user_content, datetime.datetime.now())
            self.message_input.delete("1.0", tk.END) # Clear input field
        except Exception as e:
            self.update_status_bar(f"Error saving user message: {e}", is_error=True)
            # Show type of exception for better debugging
            messagebox.showerror("DB Error", f"Could not save your message: {type(e).__name__}: {e}")
            self._enable_input()
            return

        # Prepare messages for Ollama API (history)
        try:
            db_messages = self.db_manager.get_messages(temp_conv_id)
            ollama_messages = [{"role": msg['role'], "content": msg['content']} for msg in db_messages]
        except Exception as e:
            self.update_status_bar(f"Error fetching message history: {e}", is_error=True)
            self._enable_input()
            return

        # Add a placeholder for assistant's response
        assistant_msg_id_placeholder = f"assistant_pending_{datetime.datetime.now().timestamp()}"
        self.assistant_response_content = "" # Store full response
        # The UI element for the assistant message will be created by _add_message_to_display
        # We need a way to update it. Let's create it empty first.
        self.assistant_msg_frame = self._add_message_to_display(
            assistant_msg_id_placeholder, "assistant", "[Thinking...]", datetime.datetime.now(), is_streaming=True
        )
        # Clear the "[Thinking...]" text from the Text widget inside assistant_msg_frame
        for widget in self.assistant_msg_frame.winfo_children():
            if isinstance(widget, tk.Text):
                widget.configure(state="normal")
                widget.delete("1.0", tk.END)
                # Re-insert role
                widget.insert(tk.END, f"Assistant: ", f"role_assistant")
                widget.configure(state="disabled")
                break

        # Stream chat response
        self.ollama_client.stream_chat(
            model=selected_model,
            messages=ollama_messages,
            on_chunk=self._handle_stream_chunk,
            on_complete=lambda data, cid=temp_conv_id: self._handle_stream_complete(data, cid), # Pass conv_id
            on_error=self._handle_stream_error
        )

    def _handle_stream_chunk(self, chunk):
        self.assistant_response_content += chunk
        self.queue_ui_update(self._update_streaming_message_display, self.assistant_msg_frame, chunk)
        self.queue_ui_update(self.update_status_bar, "Receiving response...", False)

    def _handle_stream_complete(self, final_data, conversation_id):
        self.queue_ui_update(self.update_status_bar, "Response complete.", False)
        self.queue_ui_update(self._enable_input)

        # Save full assistant response to DB
        try:
            # Replace the temporary message frame if it had a placeholder ID.
            # The content is already streamed. Now save to DB and update the message ID on the frame.
            if self.assistant_msg_frame and hasattr(self.assistant_msg_frame, 'message_id') and isinstance(self.assistant_msg_frame.message_id, str) and self.assistant_msg_frame.message_id.startswith("assistant_pending_"):

                final_assistant_content = self.assistant_response_content # Already accumulated
                # Update the timestamp on the frame to the final one
                ts_label = None
                for child in self.assistant_msg_frame.winfo_children():
                    if isinstance(child, ttk.Label) and "Timestamp.TLabel" in str(child.cget("style")):
                        ts_label = child
                        break

                completion_time = datetime.datetime.now()
                if 'created_at' in final_data: # Ollama's timestamp for the final chunk
                    try:
                        completion_time = datetime.datetime.fromisoformat(final_data['created_at'].replace('Z', '+00:00'))
                    except ValueError:
                        pass # Keep datetime.now()

                if ts_label:
                    self.queue_ui_update(ts_label.config, text=completion_time.strftime("%Y-%m-%d %H:%M:%S"))

                assistant_msg_id = self.db_manager.add_message(conversation_id, "assistant", final_assistant_content)
                self.assistant_msg_frame.message_id = assistant_msg_id # Update ID on the frame

                # Update conversation's updated_at (add_message in db_manager should do this)
                self.load_conversations() # Refresh list to reflect new updated_at time
                # Re-select current conversation
                for i in range(self.conversations_listbox.size()):
                    if self.conversations_listbox.get(i)[0] == conversation_id:
                        self.conversations_listbox.selection_set(i)
                        break

            self.assistant_response_content = "" # Reset for next message
            self.assistant_msg_frame = None

        except Exception as e:
            self.queue_ui_update(self.update_status_bar, f"Error saving assistant response: {e}", True)
            self.queue_ui_update(messagebox.showerror, "DB Error", f"Could not save assistant's response: {e}")

        self.queue_ui_update(self._scroll_chat_to_bottom)


    def _handle_stream_error(self, error):
        self.queue_ui_update(self.update_status_bar, f"Stream error: {error}", is_error=True)
        self.queue_ui_update(self._enable_input)
        # Remove the "Thinking..." or partially streamed message if an error occurs
        if self.assistant_msg_frame:
            self.queue_ui_update(self.assistant_msg_frame.destroy)
            self.assistant_msg_frame = None
        self.assistant_response_content = "" # Reset
        self.queue_ui_update(messagebox.showerror, "Stream Error", f"Ollama API error: {error}")

    def _enable_input(self):
        self.message_input.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.message_input.focus_set()

    def update_status_bar(self, text, is_error=False):
        self.status_bar.config(text=f"Status: {text}")
        self.status_bar.config(style="Error.TLabel" if is_error else "Status.TLabel")

    def check_ollama_status_periodically(self):
        def check_status_thread():
            # This runs in a separate thread, use queue for UI update
            connected, message = self.ollama_client.check_connection()
            if connected:
                self.queue_ui_update(self.update_status_bar, "Ollama Connected", False)
            else:
                self.queue_ui_update(self.update_status_bar, f"Ollama Connection Error: {message}", True)

            # Schedule next check (from this thread, which is fine for 'after')
            # This creates a new timer in the main Tkinter thread's event loop
            self.root.after(30000, self.check_ollama_status_periodically) # Check every 30 seconds

        # Initial check, then schedule periodic
        # Run the check in a thread to avoid blocking UI on first check
        threading.Thread(target=check_status_thread, daemon=True).start()

    def edit_selected_message(self):
        message_id = getattr(self.message_context_menu, 'message_id_to_edit', None)
        message_frame = getattr(self.message_context_menu, 'message_frame_to_edit', None)

        if not message_id or not message_frame:
            messagebox.showwarning("Edit Message", "No message selected or context lost.")
            return

        # Retrieve the original content from the Text widget within message_frame
        original_content = ""
        text_widget_to_edit = None
        for widget in message_frame.winfo_children():
            if isinstance(widget, tk.Text):
                text_widget_to_edit = widget
                original_content = widget.get("1.0", tk.END).strip()
                # The content includes "Role: Actual content". Need to strip role.
                if original_content.startswith("User: "):
                    original_content = original_content[len("User: "):]
                elif original_content.startswith("Assistant: "): # If assistant editing is allowed
                     original_content = original_content[len("Assistant: "):]
                break

        if not text_widget_to_edit:
            messagebox.showerror("Edit Error", "Cannot find text content of the message.")
            return

        new_content = simpledialog.askstring("Edit Message", "Enter new content:", initialvalue=original_content, parent=self.root)

        if new_content is None or new_content.strip() == original_content.strip():
            self.update_status_bar("Edit cancelled or no change.", False)
            return

        new_content = new_content.strip()
        if not new_content:
            messagebox.showwarning("Edit Message", "Content cannot be empty.")
            return

        # Proceed with editing
        self.update_status_bar("Processing edit...", False)
        try:
            # 1. Update the message content in the database
            self.db_manager.update_message_content(message_id, new_content)

            # 2. Delete all subsequent messages in the database for this conversation
            #    Need to get messages sorted by timestamp to find the next one.
            #    Or, db_manager.delete_messages_from needs to be smart.
            #    The current db_manager.delete_messages_from(conv_id, first_msg_id_to_delete) is what we need.
            #    We need the ID of the message *after* the edited one.

            messages_in_conv = self.db_manager.get_messages(self.current_conversation_id)
            edited_message_index = -1
            for i, msg in enumerate(messages_in_conv):
                if msg['id'] == message_id:
                    edited_message_index = i
                    break

            if edited_message_index != -1 and edited_message_index + 1 < len(messages_in_conv):
                first_message_id_to_delete = messages_in_conv[edited_message_index + 1]['id']
                self.db_manager.delete_messages_from(self.current_conversation_id, first_message_id_to_delete)

            # 3. Refresh the chat display: clear and reload messages up to the edited one
            self.on_conversation_select() # This reloads all messages for current_conversation_id

            # 4. Resend the (now tailing) conversation to Ollama from the edited point
            #    The user has to type a new message to continue, or we can auto-send the edited part.
            #    The prompt says: "Continue conversation from edited point"
            #    This implies the UI should reflect the change, and the *next* send will use this new history.
            #    No auto-resend is required by the prompt. Just that the history is now branched.

            self.update_status_bar(f"Message edited. Conversation branched.", False)

        except Exception as e:
            self.update_status_bar(f"Error editing message: {e}", is_error=True)
            messagebox.showerror("Edit Error", f"Could not process message edit: {e}")
            print(f"Edit error: {e}")


# Dummy classes for testing AppUI standalone
class DummyDBManager:
    def __init__(self):
        self.conv_id_counter = 0
        self.msg_id_counter = 0
        self.conversations = {} # id: {id, title, model, created_at, updated_at}
        self.messages = {} # id: {id, conversation_id, role, content, timestamp}
        self.initialize_db()

    def initialize_db(self):
        # Create some dummy data
        conv1_id = self.create_conversation("Greeting Chat", "phi3")
        self.add_message(conv1_id, "user", "Hello Ollama!")
        self.add_message(conv1_id, "assistant", "Hi there! How can I help you today?")

        conv2_id = self.create_conversation("Tech Questions", "llama2")
        self.add_message(conv2_id, "user", "What is Python?")

        print("DummyDB initialized with sample data.")

    def get_conversations(self):
        return sorted(list(self.conversations.values()), key=lambda c: c['updated_at'], reverse=True)

    def get_conversations_by_id(self, conv_id): # Helper added
        return self.conversations.get(conv_id)

    def get_messages(self, conversation_id):
        msgs = [m for m in self.messages.values() if m['conversation_id'] == conversation_id]
        return sorted(msgs, key=lambda m: m['timestamp'])

    def create_conversation(self, title, model):
        self.conv_id_counter += 1
        now = datetime.datetime.now()
        self.conversations[self.conv_id_counter] = {
            'id': self.conv_id_counter, 'title': title, 'model': model,
            'created_at': now, 'updated_at': now
        }
        return self.conv_id_counter

    def add_message(self, conversation_id, role, content):
        self.msg_id_counter += 1
        now = datetime.datetime.now()
        self.messages[self.msg_id_counter] = {
            'id': self.msg_id_counter, 'conversation_id': conversation_id,
            'role': role, 'content': content, 'timestamp': now
        }
        if conversation_id in self.conversations:
            self.conversations[conversation_id]['updated_at'] = now
        return self.msg_id_counter

    def delete_conversation(self, conversation_id):
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            self.messages = {mid: msg for mid, msg in self.messages.items() if msg['conversation_id'] != conversation_id}
            print(f"DummyDB: Deleted conversation {conversation_id}")
        else:
            print(f"DummyDB: Conversation {conversation_id} not found for deletion.")


    def update_conversation_model(self, conversation_id, model):
        if conversation_id in self.conversations:
            self.conversations[conversation_id]['model'] = model
            self.conversations[conversation_id]['updated_at'] = datetime.datetime.now()
            print(f"DummyDB: Updated model for conv {conversation_id} to {model}")
        else:
            print(f"DummyDB: Conversation {conversation_id} not found for model update.")

    def update_message_content(self, message_id, new_content):
        if message_id in self.messages:
            self.messages[message_id]['content'] = new_content
            self.messages[message_id]['timestamp'] = datetime.datetime.now() # Editing updates timestamp
            conv_id = self.messages[message_id]['conversation_id']
            if conv_id in self.conversations:
                 self.conversations[conv_id]['updated_at'] = datetime.datetime.now()
            print(f"DummyDB: Updated message {message_id} content.")
        else:
            print(f"DummyDB: Message {message_id} not found for content update.")

    def delete_messages_from(self, conversation_id, first_message_id_to_delete):
        # Simplified: find timestamp of first_message_id_to_delete, then delete all >= that timestamp
        if first_message_id_to_delete not in self.messages:
            print(f"DummyDB: Message {first_message_id_to_delete} (start of delete range) not found.")
            return

        ts_to_delete_from = self.messages[first_message_id_to_delete]['timestamp']

        ids_to_remove = [
            mid for mid, msg in self.messages.items()
            if msg['conversation_id'] == conversation_id and msg['timestamp'] >= ts_to_delete_from
        ]
        for mid in ids_to_remove:
            del self.messages[mid]
        print(f"DummyDB: Deleted messages from conversation {conversation_id} starting with ID {first_message_id_to_delete} (and subsequent).")
        if conversation_id in self.conversations:
            # Update 'updated_at' for the conversation
            remaining_msgs = self.get_messages(conversation_id)
            if remaining_msgs:
                self.conversations[conversation_id]['updated_at'] = remaining_msgs[-1]['timestamp']
            else:
                self.conversations[conversation_id]['updated_at'] = self.conversations[conversation_id]['created_at']


class DummyOllamaClient:
    def list_models(self):
        print("DummyClient: list_models called")
        return {"models": [{"name": "dummy-model-1", "size":123}, {"name": "phi3-mini-dummy", "size":456}]}

    def check_connection(self):
        print("DummyClient: check_connection called")
        return True, "Dummy Ollama server is responsive."

    def stream_chat(self, model, messages, on_chunk, on_complete, on_error):
        print(f"DummyClient: stream_chat called for model {model} with messages: {messages[-1]['content']}")

        self.stop_event = threading.Event()

        def dummy_stream_worker():
            dummy_response = f"This is a dummy streamed response from {model} to your message: '{messages[-1]['content']}'. "
            words = dummy_response.split()
            try:
                for i, word in enumerate(words):
                    if self.stop_event.is_set():
                        print("Dummy stream worker: Stop event set, exiting.")
                        on_error("Stream stopped by user")
                        return

                    time.sleep(0.1) # Simulate network latency
                    on_chunk(word + " ")
                    if i == len(words) -1 : # last word
                        on_chunk("\n") # Add a newline at the end for clarity

                # Simulate final data object
                final_data = {
                    "model": model,
                    "created_at": datetime.datetime.now().isoformat() + "Z",
                    "message": {"role": "assistant", "content": dummy_response.strip()},
                    "done": True,
                    "done_reason": "stop"
                }
                on_complete(final_data)
            except Exception as e:
                print(f"Dummy stream worker error: {e}")
                on_error(e)

        threading.Thread(target=dummy_stream_worker, daemon=True).start()
        return self.stop_event

    def stop_current_stream(self):
        if hasattr(self, 'stop_event') and self.stop_event:
            self.stop_event.set()
            print("DummyClient: stop_current_stream called, stop_event set.")


if __name__ == '__main__':
    import time # for dummy client
    root = tk.Tk()
    # Use dummy clients for standalone testing
    dummy_db = DummyDBManager()
    dummy_ollama = DummyOllamaClient()

    app = AppUI(root, dummy_db, dummy_ollama)
    root.mainloop()
