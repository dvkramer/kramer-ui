import customtkinter as ctk
import ollama
from ollama import Client
import threading
import json
from datetime import datetime
import re

# --- Constants ---
APP_NAME = "Kramer UI for Ollama"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
OLLAMA_HOST = 'http://127.0.0.1:11434'
MAX_CHAT_WIDTH = 1000  # Maximum width for chat area

# Modern color scheme
COLORS = {
    'bg': '#0f172a',
    'surface': '#1e293b',
    'surface_light': '#334155',
    'accent': '#3b82f6',
    'accent_hover': '#2563eb',
    'text': '#f1f5f9',
    'text_muted': '#94a3b8',
    'user_bubble': '#3b82f6',
    'ai_bubble': '#374151',
    'success': '#10b981',
    'error': '#ef4444'
}

class OllamaGuiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(APP_NAME)
        self.after(0, lambda: self.state('zoomed'))  # Delayed zoom
        self.minsize(600, 500)
        
        # Set dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Configure window
        self.configure(fg_color=COLORS['bg'])
        
        # Initialize Ollama client
        self.client = Client(host=OLLAMA_HOST)
        
        # App state
        self.conversation_history = []
        self.selected_model = ctk.StringVar()
        self.is_generating = False
        self.editing_frame = None # Frame for inline editing UI
        self.active_edit_button = None # Store the currently disabled edit button
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()
        self.after(100, self._initialize_app)
    
    def _create_widgets(self):
        """Create all UI widgets"""
        # Header with model selector
        self._create_header()
        
        # Main container for chat area with width constraint
        self._create_main_container()
        
        # Chat area
        self._create_chat_area()
        
        # Input area
        self._create_input_area()
        
        # Status bar
        self._create_status_bar()
    
    def _create_header(self):
        """Create header with model selector and controls"""
        self.header_frame = ctk.CTkFrame(
            self, 
            height=60, 
            corner_radius=0,
            fg_color=COLORS['surface']
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # App title
        title_label = ctk.CTkLabel(
            self.header_frame, 
            text="🦙 Kramer UI for Ollama", 
            font=ctk.CTkFont(size=20, weight="bold"),  # Increased from 18
            text_color=COLORS['text']
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Model selector
        model_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        model_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        model_label = ctk.CTkLabel(
            model_frame, 
            text="Model:", 
            font=ctk.CTkFont(size=14),  # Increased from 12
            text_color=COLORS['text_muted']
        )
        model_label.grid(row=0, column=0, padx=(0, 10))
        
        self.model_selector = ctk.CTkOptionMenu(
            model_frame,
            variable=self.selected_model,
            values=["Loading..."],
            state="disabled",
            width=200,
            font=ctk.CTkFont(size=14),  # Added font size
            fg_color=COLORS['surface_light'],
            button_color=COLORS['accent'],
            button_hover_color=COLORS['accent_hover']
        )
        self.model_selector.grid(row=0, column=1)
        
        # New chat button
        self.new_chat_btn = ctk.CTkButton(
            model_frame,
            text="New Chat",
            command=self._new_chat,
            width=80,
            height=32,
            fg_color=COLORS['surface_light'],
            hover_color=COLORS['accent'],
            font=ctk.CTkFont(size=14)  # Increased from 12
        )
        self.new_chat_btn.grid(row=0, column=2, padx=(15, 0))
    
    def _create_main_container(self):
        """Create main container with width constraint"""
        self.main_container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.main_container.grid(row=1, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(1, weight=1)  # Center column expands
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Left spacer
        left_spacer = ctk.CTkFrame(self.main_container, fg_color="transparent", width=0)
        left_spacer.grid(row=0, column=0, sticky="nsew")
        
        # Chat container with max width
        self.chat_container = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent",
            width=MAX_CHAT_WIDTH
        )
        self.chat_container.grid(row=0, column=1, sticky="nsew", padx=20)
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(1, weight=0)
        
        # Right spacer
        right_spacer = ctk.CTkFrame(self.main_container, fg_color="transparent", width=0)
        right_spacer.grid(row=0, column=2, sticky="nsew")
        
        # Bind to window resize to enforce max width
        self.bind("<Configure>", self._on_window_resize)
    
    def _on_window_resize(self, event):
        """Handle window resize to maintain max chat width"""
        if event.widget == self:
            window_width = self.winfo_width()
            if window_width > MAX_CHAT_WIDTH + 40:  # 40 for padding
                # Calculate side padding to center the chat
                side_padding = (window_width - MAX_CHAT_WIDTH) // 2
                self.chat_container.grid_configure(padx=side_padding)
            else:
                self.chat_container.grid_configure(padx=20)
    
    def _create_chat_area(self):
        """Create scrollable chat area"""
        self.chat_frame = ctk.CTkScrollableFrame(
            self.chat_container,
            corner_radius=0,
            fg_color=COLORS['bg'],
            scrollbar_button_color=COLORS['surface_light'],
            scrollbar_button_hover_color=COLORS['accent']
        )
        self.chat_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.chat_frame.grid_columnconfigure(0, weight=1)
    
    def _create_input_area(self):
        """Create input area with text box and send button"""
        self.input_frame = ctk.CTkFrame(
            self.chat_container,
            height=80,
            corner_radius=15,
            fg_color=COLORS['surface']
        )
        self.input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Input text box
        self.user_input = ctk.CTkTextbox(
            self.input_frame,
            height=40,
            corner_radius=10,
            fg_color=COLORS['surface_light'],
            border_color=COLORS['surface_light'],
            font=ctk.CTkFont(size=14)  # Increased from 12
        )
        self.user_input.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        self.user_input.bind("<Return>", self._on_enter_key)
        self.user_input.bind("<Shift-Return>", self._on_shift_enter)
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="Send",
            command=self._send_message,
            width=80,
            height=40,
            corner_radius=10,
            fg_color=COLORS['accent'],
            hover_color=COLORS['accent_hover'],
            font=ctk.CTkFont(size=14, weight="bold")  # Increased from 12
        )
        self.send_button.grid(row=0, column=1, padx=(0, 15), pady=15)
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        self.status_frame = ctk.CTkFrame(
            self,
            height=25,
            corner_radius=0,
            fg_color=COLORS['surface']
        )
        self.status_frame.grid(row=2, column=0, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=f"Connecting to {OLLAMA_HOST}...",
            font=ctk.CTkFont(size=12),  # Increased from 10
            text_color=COLORS['text_muted']
        )
        self.status_label.pack(side="left", padx=10, pady=2)
    
    def _initialize_app(self):
        """Initialize the app by fetching models"""
        self._update_status("Connecting to Ollama server...")
        threading.Thread(target=self._fetch_models, daemon=True).start()
    
    def _fetch_models(self):
        """Fetch available models from Ollama"""
        try:
            response = self.client.list()
            print(f"DEBUG: Raw response: {response}")  # Debug output
            
            models = response.get('models', [])
            print(f"DEBUG: Models found: {models}")  # Debug output
            
            if not models:
                self.after(0, self._handle_no_models)
                return
            
            # Extract model names from Model objects
            model_names = []
            for model in models:
                if hasattr(model, 'model'):
                    model_names.append(model.model)
                elif isinstance(model, dict) and 'name' in model:
                    model_names.append(model['name'])
                elif isinstance(model, dict) and 'model' in model:
                    model_names.append(model['model'])
            
            print(f"DEBUG: Model names: {model_names}")  # Debug output
            
            if not model_names:
                self.after(0, self._handle_no_models)
                return
                
            self.after(0, self._update_model_list, model_names)
            
        except Exception as e:
            print(f"DEBUG: Exception: {e}")  # Debug output
            self.after(0, self._handle_connection_error, str(e))
    
    def _update_model_list(self, model_names):
        """Update the model selector with available models"""
        if not model_names:
            self._handle_no_models()
            return
            
        self.model_selector.configure(values=model_names, state="normal")
        self.selected_model.set(model_names[0])
        self._update_status(f"Ready • {len(model_names)} models available")
    
    def _handle_no_models(self):
        """Handle case when no models are available"""
        self.model_selector.configure(values=["No models found"], state="disabled")
        self._update_status("No models found. Run 'ollama pull <model>' to install a model.")
    
    def _handle_connection_error(self, error):
        """Handle connection errors"""
        self.model_selector.configure(values=["Connection Error"], state="disabled")
        self._update_status(f"Connection failed: {error}")
    
    def _update_status(self, message):
        """Update status bar message"""
        self.status_label.configure(text=message)
    
    def _parse_thinking_content(self, content):
        """Parse content to separate thinking sections from regular content"""
        # Pattern to match <think>...</think> blocks
        think_pattern = r'<think>(.*?)</think>'
        
        # Find all thinking blocks
        thinking_blocks = re.findall(think_pattern, content, re.DOTALL)
        
        # Remove thinking blocks from main content
        clean_content = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
        
        return clean_content, thinking_blocks
    
    def _create_thinking_dropdown(self, parent, thinking_blocks):
        """Create a collapsible dropdown for thinking content"""
        if not thinking_blocks:
            return None
        
        # Create dropdown frame
        dropdown_frame = ctk.CTkFrame(parent, fg_color="transparent")
        dropdown_frame.pack(fill="x", padx=18, pady=(0, 8))
        
        # Create toggle button
        self.thinking_expanded = False
        toggle_btn = ctk.CTkButton(
            dropdown_frame,
            text="▶ Show Thinking",
            command=lambda: self._toggle_thinking(dropdown_frame, toggle_btn, thinking_blocks),
            width=120,
            height=28,
            fg_color=COLORS['surface_light'],
            hover_color=COLORS['surface'],
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_muted']
        )
        toggle_btn.pack(anchor="w", pady=(0, 5))
        
        return dropdown_frame
    
    def _toggle_thinking(self, dropdown_frame, toggle_btn, thinking_blocks):
        """Toggle the thinking content visibility"""
        # Check if thinking content already exists
        thinking_content = None
        for widget in dropdown_frame.winfo_children():
            if isinstance(widget, ctk.CTkTextbox):
                thinking_content = widget
                break
        
        if thinking_content:
            # Hide thinking content
            thinking_content.destroy()
            toggle_btn.configure(text="▶ Show Thinking")
            self.thinking_expanded = False
        else:
            # Show thinking content
            thinking_text = "\n\n".join(thinking_blocks)
            thinking_content = ctk.CTkTextbox(
                dropdown_frame,
                height=min(200, len(thinking_text.split('\n')) * 20 + 40),
                corner_radius=8,
                fg_color=COLORS['surface'],
                border_color=COLORS['surface_light'],
                font=ctk.CTkFont(size=13),
                text_color=COLORS['text_muted'],
                wrap="word"
            )
            thinking_content.pack(fill="x", pady=(0, 5))
            thinking_content.insert("0.0", thinking_text)
            thinking_content.configure(state="disabled")
            
            toggle_btn.configure(text="▼ Hide Thinking")
            self.thinking_expanded = True
        
        self._scroll_to_bottom()
    
    def _add_message(self, role, content, is_streaming=False):
        """Add a message bubble to the chat"""
        # Create message container
        msg_container = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        msg_container.grid(row=len(self.chat_frame.winfo_children()), column=0, sticky="ew", pady=8)  # Increased padding
        msg_container.grid_columnconfigure(0, weight=1)
        
        # Configure alignment and colors
        if role == "user":
            anchor = "right"
            bg_color = COLORS['user_bubble']
            text_color = "white"
            clean_content = content
            thinking_blocks = []
        else:
            anchor = "left"
            bg_color = COLORS['ai_bubble']
            text_color = COLORS['text']
            # Parse thinking content for AI messages
            clean_content, thinking_blocks = self._parse_thinking_content(content)
        
        # Create message bubble
        bubble = ctk.CTkFrame(
            msg_container,
            fg_color=bg_color,
            corner_radius=15
        )
        bubble.pack(side=anchor, padx=10, fill="x" if role == "assistant" else "none", expand=True if role == "assistant" else False)
        
        # Add thinking dropdown if there are thinking blocks (AI messages only)
        if role == "assistant" and thinking_blocks and not is_streaming:
            self._create_thinking_dropdown(bubble, thinking_blocks)
        
        # Add message content (cleaned of thinking tags)
        display_content = clean_content if clean_content.strip() else content
        message_label = ctk.CTkLabel(
            bubble,
            text=display_content,
            font=ctk.CTkFont(size=15),  # Increased from 12
            text_color=text_color,
            wraplength=700,  # Increased from 600
            justify="left"
        )
        message_label.pack(padx=18, pady=12, anchor="w")  # Increased padding

        # --- Add Edit button for completed user messages (outside the bubble) ---
        if role == "user" and not is_streaming:
            # Edit button goes into msg_container, aligned to the side of/below the bubble
            edit_button_container = ctk.CTkFrame(msg_container, fg_color="transparent")
            # Pack timestamp first, then edit button container
            # Timestamp will be packed based on 'anchor'

            timestamp = datetime.now().strftime("%H:%M")
            time_label = ctk.CTkLabel(
                msg_container,
                text=timestamp,
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_muted']
            )
            time_label.pack(side=anchor, padx=15, pady=(0,0), anchor="s")

            edit_button_container.pack(side=anchor, fill="x", padx=10, pady=(2,5))

            edit_button = ctk.CTkButton(
                edit_button_container,
                text="✏️",  # Emoji for Edit
                font=None, # Use default font for better emoji rendering potentially
                width=30,
                height=30,
                fg_color=COLORS['surface_light'],
                hover_color=COLORS['accent']
            )
            current_message_index = len(self.conversation_history)
            # edit_button_container is the parent of edit_button. msg_container is parent of edit_button_container.
            edit_button.configure(command=lambda idx=current_message_index, btn=edit_button: self._start_edit(idx, btn))
            edit_button.pack(side="right" if anchor == "right" else "left", padx=5)

        elif not is_streaming: # For AI messages, just add timestamp
            timestamp = datetime.now().strftime("%H:%M")
            time_label = ctk.CTkLabel(
                msg_container,
                text=timestamp,
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_muted']
            )
            time_label.pack(side=anchor, padx=15, pady=(0, 5), anchor="s")

        # self._scroll_to_bottom() is now typically called by _re_grid_chat_widgets
        # However, for streaming, we might want to ensure scroll happens.
        if is_streaming:
            self._scroll_to_bottom()
        elif self.editing_frame is None : # Only regrid if not in an active edit sequence that will handle it
             self.after(10, self._re_grid_chat_widgets) # Use self.after to allow current UI changes to process

        return message_label

    def _scroll_to_widget(self, widget):
        """Scroll chat to make the specified widget visible."""
        if not widget or not widget.winfo_exists():
            return # Widget is None or has been destroyed

        self.chat_frame._parent_canvas.update_idletasks()

        try:
            # Ensure widget geometry is up to date
            widget.update_idletasks()

            canvas_height = self.chat_frame._parent_canvas.winfo_height()
            widget_y = widget.winfo_y() # Y position of widget within chat_frame
            widget_h = widget.winfo_height()
            content_height = self.chat_frame.winfo_height() # Total height of the content within scrollable area

            if content_height <= canvas_height:
                return # No scroll needed if content is smaller than canvas

            # Desired position: try to bring the widget into the middle of the view
            # target_y_on_canvas = widget_y - (canvas_height / 2) + (widget_h / 2)
            # Simplified: scroll to bring the top of the widget into view, with a small margin
            target_y_on_canvas = widget_y - 10 # 10px margin

            scroll_value = target_y_on_canvas / content_height
            scroll_value = max(0.0, min(1.0, scroll_value)) # Clamp between 0 and 1

            self.chat_frame._parent_canvas.yview_moveto(scroll_value)
        except Exception as e:
            print(f"Error in _scroll_to_widget: {e}")


    def _scroll_to_bottom(self):
        """Scroll chat to bottom"""
        # Ensure all pending UI operations are done so scroll is accurate
        self.chat_frame._parent_canvas.update_idletasks()
        self.after(10, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
    
    def _on_enter_key(self, event):
        """Handle Enter key press"""
        if not event.state & 0x1:  # No Shift key
            self._send_message()
            return "break"
        return None
    
    def _on_shift_enter(self, event):
        """Handle Shift+Enter for new lines"""
        return None
    
    def _send_message(self):
        """Send user message and get AI response"""
        user_text = self.user_input.get("1.0", "end-1c").strip()
        
        if not user_text or self.is_generating or self.model_selector.cget("state") == "disabled":
            return
        
        # Add user message
        self._add_message("user", user_text)
        self.conversation_history.append({"role": "user", "content": user_text})
        
        # Clear input
        self.user_input.delete("1.0", "end")
        
        # Start generating response
        self.is_generating = True
        self._toggle_input(False)
        self._update_status("Generating response...")
        
        # Add AI message placeholder
        ai_label = self._add_message("assistant", "●●●", is_streaming=True)
        
        # Start streaming in background
        threading.Thread(
            target=self._stream_response,
            args=(self.conversation_history.copy(), ai_label),
            daemon=True
        ).start()
    
    def _stream_response(self, history, ai_label):
        """Stream AI response"""
        model = self.selected_model.get()
        full_response = ""
        
        try:
            stream = self.client.chat(model=model, messages=history, stream=True)
            
            for chunk in stream:
                if not self.is_generating:  # Check if cancelled
                    break
                    
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    
                    # For streaming, show raw content but parse for final display
                    display_content = full_response
                    if '<think>' in full_response and '</think>' in full_response:
                        clean_content, _ = self._parse_thinking_content(full_response)
                        if clean_content.strip():
                            display_content = clean_content
                    
                    self.after(0, lambda: ai_label.configure(text=display_content))
                    self.after(0, self._scroll_to_bottom)
            
            # After streaming is complete, recreate the message with proper thinking dropdown
            if full_response.strip():
                # Remove the streaming message
                ai_label.master.master.destroy()
                
                # Add the final message with thinking dropdown
                self._add_message("assistant", full_response)
                
                # Add to conversation history
                self.conversation_history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.after(0, lambda: ai_label.configure(text=error_msg))
            self.after(0, self._update_status, f"Error: {str(e)}")
        
        finally:
            self.is_generating = False
            self.after(0, self._toggle_input, True)
            self.after(0, self._update_status, "Ready")
    
    def _toggle_input(self, enabled):
        """Toggle input widgets, including the New Chat button."""
        input_state = "normal" if enabled else "disabled"

        # Send button
        self.send_button.configure(state=input_state)

        # New Chat button
        if hasattr(self, 'new_chat_btn'): # Ensure new_chat_btn exists
            self.new_chat_btn.configure(state=input_state)
        
        # Always keep the input box enabled and focused,
        # actual sending is blocked by self.is_generating and send_button state.
        self.user_input.configure(state="normal")
        if enabled: # Only focus if we are enabling input
            self.user_input.focus()
    
    def _new_chat(self):
        """Start a new chat"""
        self.conversation_history.clear()
        
        # Clear chat area
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        
        self._update_status("New chat started")
        self.user_input.focus()

    def _re_grid_chat_widgets(self):
        """Re-apply grid layout to all direct children of self.chat_frame.
        This ensures sequential rows and consistent padding, especially when
        the editing_frame is added or removed.
        """
        current_row = 0
        children_snapshot = list(self.chat_frame.winfo_children()) # Iterate over a copy

        for widget in children_snapshot:
            if not widget.winfo_exists():
                continue

            common_padx = 0 # Children span full width due to sticky='ew' in their grid config

            if widget == self.editing_frame and self.editing_frame is not None:
                # Specific pady for editing_frame for some spacing
                widget.grid(row=current_row, column=0, sticky="ew", padx=common_padx, pady=(5, 10))
            else: # Assumed to be a msg_container or other standard chat widget
                  # Check if it's a CCTkFrame, as msg_container is one. This avoids errors if other non-frame widgets exist.
                if isinstance(widget, ctk.CTkFrame):
                    widget.grid(row=current_row, column=0, sticky="ew", padx=common_padx, pady=8) # Standard pady for msg_containers
                else: # Fallback for other widget types, though not expected as direct children needing re-grid.
                    widget.grid(row=current_row, column=0, sticky="ew")
            current_row += 1

        self.after(20, self._scroll_to_bottom) # Ensure layout update is visible and scrolled if needed


    def _clear_chat_from_index(self, start_idx):
        """Remove message containers from the UI from start_idx onwards."""
        all_msg_containers = self.chat_frame.winfo_children()

        if start_idx < 0:
            start_idx = 0

        widgets_to_destroy = all_msg_containers[start_idx:]

        for widget in widgets_to_destroy:
            widget.destroy()

        # After removing widgets, re-grid the remaining ones.
        self._re_grid_chat_widgets()


    def _start_edit(self, msg_idx, edit_button_widget):
        """Begin editing a user message by showing an editing UI below it."""
        if self.is_generating:
            return

        if self.editing_frame: # If another edit is active, cancel it first
            self._cancel_edit()

        self._toggle_input(False) # Disable main chat input

        try:
            # edit_button_widget.master is edit_button_container. Its master is target_msg_container.
            target_msg_container = edit_button_widget.master.master
            original_content = self.conversation_history[msg_idx]['content']
        except IndexError:
            print(f"Error: Message index {msg_idx} out of bounds for editing.")
            self._toggle_input(True)
            return
        except AttributeError: # If widget hierarchy is not as expected
            print(f"Error: Could not find target_msg_container for editing via button.")
            self._toggle_input(True)
            return

        self.active_edit_button = edit_button_widget
        self.active_edit_button.configure(state="disabled")

        # Create the editing frame
        self.editing_frame = ctk.CTkFrame(self.chat_frame, fg_color=COLORS['surface'], corner_radius=10)

        edit_textbox = ctk.CTkTextbox(
            self.editing_frame,
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text'],
            fg_color=COLORS['surface_light'],
            border_color=COLORS['accent'],
            border_width=1,
            wrap="word"
        )
        edit_textbox.insert("0.0", original_content)
        edit_textbox.pack(padx=10, pady=10, fill="x", expand=True)
        edit_textbox.focus()

        # Calculate required height for textbox (approx based on lines and font size)
        # This is a rough estimation.
        text_lines = original_content.count('\n') + 1
        estimated_height = text_lines * 20 + 30 # 20px per line + padding
        edit_textbox.configure(height=min(max(80, estimated_height), 200))


        # Edit action buttons frame within editing_frame
        actions_frame = ctk.CTkFrame(self.editing_frame, fg_color="transparent")
        actions_frame.pack(fill="x", padx=10, pady=(0, 10), anchor="e")

        save_button = ctk.CTkButton(
            actions_frame,
            text="✔️",  # Changed Emoji for Save
            command=lambda: self._save_edit(msg_idx, edit_textbox),
            width=30, # Adjusted width
            height=30, # Adjusted height
            font=None, # Use default font
            fg_color=COLORS['success']
        )
        save_button.pack(side="right", padx=(5,0))

        cancel_button = ctk.CTkButton(
            actions_frame,
            text="❌",  # Emoji for Cancel
            command=self._cancel_edit,
            width=30, # Adjusted width
            height=30, # Adjusted height
            font=None, # Use default font
            fg_color=COLORS['error']
        )
        cancel_button.pack(side="right", padx=(0,5))

        # Place editing_frame (it will be gridded by _re_grid_chat_widgets)
        # The editing_frame is temporarily gridded here to get its initial size/content rendered.
        # _re_grid_chat_widgets will then place it correctly among other widgets.
        # The row msg_idx + 1 is a temporary assignment.
        self.editing_frame.grid(row=msg_idx + 1, column=0, sticky="ew", padx=0, pady=(5,10))

        # Ensure the column configuration of chat_frame allows expansion for editing_frame
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self._re_grid_chat_widgets() # Call to fix layout
        self.after(100, lambda: self._scroll_to_widget(self.editing_frame))


    def _save_edit(self, msg_idx, textbox_widget):
        """Save the edited message, truncate history, and trigger new AI response."""
        new_text = textbox_widget.get("1.0", "end-1c").strip()

        if not new_text:
            # Simple cancel if new text is empty. Could also show a small error.
            self._cancel_edit()
            return

        # 1. Update conversation_history at msg_idx
        self.conversation_history[msg_idx]['content'] = new_text

        # 2. Update the original message bubble's label
        try:
            # msg_container -> bubble -> message_label
            msg_container_to_update = self.chat_frame.winfo_children()[msg_idx]
            bubble_to_update = None
            message_label_to_update = None

            for child in msg_container_to_update.winfo_children():
                if isinstance(child, ctk.CTkFrame): # This should be the bubble or edit_button_container
                    # Check if it's the bubble (has a label as a child, or specific name if we set one)
                    is_bubble = False
                    for sub_child in child.winfo_children():
                        if isinstance(sub_child, ctk.CTkLabel):
                            is_bubble = True
                            message_label_to_update = sub_child
                            break
                    if is_bubble:
                        bubble_to_update = child # Found the bubble
                        break

            if message_label_to_update:
                message_label_to_update.configure(text=new_text)
            else:
                print(f"DEBUG: Could not find message_label in msg_idx {msg_idx} to update text.")
        except Exception as e:
            print(f"Error updating message label text: {e}")


        # 3. Clean up editing UI
        if self.editing_frame:
            self.editing_frame.destroy()
            self.editing_frame = None
        if self.active_edit_button:
            self.active_edit_button.configure(state="normal")
            self.active_edit_button = None

        # 4. Truncate UI and history AFTER editing UI is gone and original message updated
        self.conversation_history = self.conversation_history[:msg_idx + 1]
        # _clear_chat_from_index will call _re_grid_chat_widgets
        self._clear_chat_from_index(msg_idx + 1)

        # 5. Trigger new AI response
        # No explicit call to _re_grid_chat_widgets here, as _clear_chat_from_index and subsequent _add_message calls will handle it.
        if self.model_selector.cget("state") == "disabled":
            self._update_status("Cannot generate response: No model selected or connection error.")
            self._toggle_input(True) # Re-enable main input as no AI response will come
            return

        self.is_generating = True
        self._toggle_input(False) # Disable main input during generation
        self._update_status("Generating response...")

        # Add AI message placeholder
        # Note: _add_message adds a new msg_container at the end of self.chat_frame.winfo_children()
        ai_label = self._add_message("assistant", "●●●", is_streaming=True)

        # History for AI is the now-truncated self.conversation_history
        history_for_ai = self.conversation_history.copy()

        threading.Thread(
            target=self._stream_response,
            args=(history_for_ai, ai_label), # _stream_response will append AI response to self.conversation_history
            daemon=True
        ).start()

        self.after(100, self._scroll_to_bottom)

    # _start_regenerate method removed

    def _cancel_edit(self):
        """Cancel editing and remove the editing UI."""
        if self.editing_frame:
            self.editing_frame.destroy()
            self.editing_frame = None

        if self.active_edit_button:
            self.active_edit_button.configure(state="normal")
            self.active_edit_button = None

        self._re_grid_chat_widgets() # Re-grid after removing editing_frame

        self._toggle_input(True) # Re-enable main input
        self.after(100, self._scroll_to_bottom) # Scroll to ensure context is reasonable


if __name__ == "__main__":
    app = OllamaGuiApp()
    app.mainloop()