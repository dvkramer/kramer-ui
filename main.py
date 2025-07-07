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
        # Create message container (this is the outer row)
        msg_container = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        msg_container.grid(row=len(self.chat_frame.winfo_children()), column=0, sticky="ew", pady=8)
        msg_container.grid_columnconfigure(0, weight=1)

        # Configure alignment and colors based on role
        if role == "user":
            anchor = "right"
            bg_color = COLORS['user_bubble']
            text_color = "white"
            clean_content = content
            thinking_blocks = []
        else:  # assistant
            anchor = "left"
            bg_color = COLORS['ai_bubble']
            text_color = COLORS['text']
            clean_content, thinking_blocks = self._parse_thinking_content(content)

        # Create a wrapper to stack bubble and controls vertically
        vertical_stack = ctk.CTkFrame(msg_container, fg_color="transparent")
        vertical_stack.pack(
            side=anchor,
            padx=10,
            fill="x" if role == "assistant" else "none",
            expand=True if role == "assistant" else False,
            anchor="n"  # Align the whole stack to the top of its row
        )

        # Create message bubble, now a child of the vertical_stack
        bubble = ctk.CTkFrame(
            vertical_stack,
            fg_color=bg_color,
            corner_radius=15
        )
        bubble.pack(fill="x", expand=True)  # Bubble fills the stack horizontally

        # Add thinking dropdown if there are thinking blocks (AI messages only)
        if role == "assistant" and thinking_blocks and not is_streaming:
            self._create_thinking_dropdown(bubble, thinking_blocks)

        # Add message content (cleaned of thinking tags)
        display_content = clean_content if clean_content.strip() else content
        message_label = ctk.CTkLabel(
            bubble,
            text=display_content,
            font=ctk.CTkFont(size=15),
            text_color=text_color,
            wraplength=700,
            justify="left"
        )
        message_label.pack(padx=18, pady=12, anchor="w")

        # --- Add controls and timestamp below the bubble for completed messages ---
        if not is_streaming:
            # Create a container for timestamp and buttons, packed below the bubble
            controls_frame = ctk.CTkFrame(vertical_stack, fg_color="transparent")
            controls_frame.pack(fill="x", padx=5, pady=(2, 0))
            controls_frame.grid_columnconfigure(0, weight=1)  # Make left side expandable

            # Timestamp
            timestamp = datetime.now().strftime("%H:%M")
            time_label = ctk.CTkLabel(
                controls_frame,
                text=timestamp,
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_muted']
            )
            # Align timestamp to the natural side of the bubble
            time_label.grid(row=0, column=0, sticky="w" if role == "assistant" else "e")

            # Add edit button ONLY for user messages
            if role == "user":
                current_message_index = len(self.conversation_history)
                # --- FIX STARTS HERE ---
                # 1. Create the button first without the command
                edit_button = ctk.CTkButton(
                    controls_frame,
                    text="✍️",
                    font=ctk.CTkFont(size=24),
                    width=28,
                    height=28,
                    fg_color="transparent",
                    hover_color=COLORS['surface_light']
                )
                # 2. Now that the button object exists, configure its command
                edit_button.configure(command=lambda idx=current_message_index, btn=edit_button: self._start_edit(idx, btn))
                # 3. Place the button on the grid
                edit_button.grid(row=0, column=1, sticky="e")
                # --- FIX ENDS HERE ---


        self._scroll_to_bottom()
        return message_label
    
    def _scroll_to_bottom(self):
        """Scroll chat to bottom"""
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
                ai_label.master.master.master.destroy() # label -> bubble -> vertical_stack -> msg_container
                
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

    def _clear_chat_from_index(self, start_idx):
        """Remove message containers from the UI from start_idx onwards."""
        # msg_containers are direct children of self.chat_frame
        all_msg_containers = self.chat_frame.winfo_children()

        # Ensure start_idx is within bounds
        if start_idx < 0:
            start_idx = 0

        for i in range(len(all_msg_containers) -1, start_idx -1, -1):
            if i < len(all_msg_containers): # double check to prevent race conditions if list changes
                all_msg_containers[i].destroy()

    def _start_edit(self, msg_idx, edit_button_widget):
        """Begin editing a user message."""
        if self.is_generating: # Don't allow edit if AI is generating
            return

        self._toggle_input(False) # Disable main input

        try:
            # button -> controls_frame -> vertical_stack -> bubble is sibling
            vertical_stack = edit_button_widget.master.master
            bubble_widget = vertical_stack.winfo_children()[0] # The bubble is the first child
            original_content = self.conversation_history[msg_idx]['content']
        except IndexError:
            print(f"Error: Message index {msg_idx} out of bounds.")
            self._toggle_input(True)
            return
        except AttributeError:
            print(f"Error: Could not find bubble widget for editing.")
            self._toggle_input(True)
            return

        # Hide the original controls (the frame with the edit button and timestamp)
        edit_button_widget.master.pack_forget()

        # Store original children of the bubble
        original_children = []
        for child in bubble_widget.winfo_children():
            original_children.append(child)

        # Clear current bubble content (message_label)
        for child in original_children:
            child.pack_forget()

        # Create editing UI inside the bubble
        edit_textbox = ctk.CTkTextbox(
            bubble_widget,
            font=ctk.CTkFont(size=15),
            fg_color=COLORS['surface_light'],
            border_color=COLORS['surface_light'],
            text_color=COLORS['text'],
            height=max(100, bubble_widget.winfo_height()),
            wrap="word"
        )
        edit_textbox.insert("0.0", original_content)
        edit_textbox.pack(padx=10, pady=10, fill="both", expand=True)
        edit_textbox.focus()

        # Edit action buttons frame (remains inside bubble for context)
        actions_frame = ctk.CTkFrame(bubble_widget, fg_color="transparent")
        actions_frame.pack(fill="x", padx=10, pady=(0,10), anchor="e")

        save_button = ctk.CTkButton(
            actions_frame,
            text="✔️",
            command=lambda: self._save_edit(msg_idx, edit_textbox, bubble_widget, original_children),
            font=ctk.CTkFont(size=18),
            width=28, height=28,
            fg_color="transparent",
            hover_color=COLORS['surface_light']
        )
        save_button.pack(side="right", padx=(5,0))

        cancel_button = ctk.CTkButton(
            actions_frame,
            text="❌",
            command=lambda: self._cancel_edit(msg_idx, bubble_widget, original_children, original_content),
            font=ctk.CTkFont(size=18),
            width=28, height=28,
            fg_color="transparent",
            hover_color=COLORS['surface_light']
        )
        cancel_button.pack(side="right", padx=(0,5))

        self.after(100, self._scroll_to_bottom)


    def _save_edit(self, msg_idx, textbox_widget, bubble_widget, original_bubble_children):
        """Save the edited message, truncate history, and trigger new AI response."""
        new_text = textbox_widget.get("1.0", "end-1c").strip()

        if not new_text: # Do not save if text is empty, maybe show a small error or just cancel
            self._cancel_edit(msg_idx, bubble_widget, original_bubble_children, self.conversation_history[msg_idx]['content'])
            return

        # 1. Update conversation_history at msg_idx
        self.conversation_history[msg_idx]['content'] = new_text

        # 2. Truncate UI - Remove all messages after the current one being edited
        self._clear_chat_from_index(msg_idx + 1)

        # 3. Truncate conversation_history list
        self.conversation_history = self.conversation_history[:msg_idx + 1]

        # 4. Restore the edited message bubble's original UI with new text
        for widget in bubble_widget.winfo_children():
            if widget not in original_bubble_children:
                widget.destroy()

        for child_widget in original_bubble_children:
            if isinstance(child_widget, ctk.CTkLabel):
                child_widget.configure(text=new_text)
                child_widget.pack(padx=18, pady=12, anchor="w")
            elif isinstance(child_widget, ctk.CTkFrame):
                child_widget.pack(fill="x", padx=10, pady=(0, 5))
            else:
                child_widget.pack()
        
        # Restore the original controls frame that was hidden
        # The bubble's parent is the vertical_stack
        vertical_stack = bubble_widget.master
        # The controls frame is the second child of the stack
        if len(vertical_stack.winfo_children()) > 1:
            controls_frame = vertical_stack.winfo_children()[1]
            controls_frame.pack(fill="x", padx=5, pady=(2, 0)) # Re-pack it
            
        # 5. Trigger new AI response
        if self.model_selector.cget("state") == "disabled":
            self._update_status("Cannot generate response: No model selected or connection error.")
            self._toggle_input(True)
            return

        self.is_generating = True
        self._toggle_input(False)
        self._update_status("Generating response...")

        ai_label = self._add_message("assistant", "●●●", is_streaming=True)
        history_for_ai = self.conversation_history.copy()

        threading.Thread(
            target=self._stream_response,
            args=(history_for_ai, ai_label),
            daemon=True
        ).start()

        self.after(100, self._scroll_to_bottom)

    def _start_regenerate(self, msg_idx, regenerate_button_widget):
        """Regenerate an AI response."""
        if self.is_generating: # Prevent multiple generations
            return

        if msg_idx <= 0: # Cannot regenerate if there's no preceding user message
            print("DEBUG: Cannot regenerate AI message at index 0 or invalid index.")
            return

        # Briefly disable the button - it will be destroyed and recreated anyway
        if regenerate_button_widget and regenerate_button_widget.winfo_exists():
            regenerate_button_widget.configure(state="disabled")

        self.is_generating = True
        self._toggle_input(False)
        self._update_status("Regenerating response...")

        # 1. Truncate conversation_history to exclude the old AI message and anything after
        # The history should contain messages UP TO the user message that prompted the AI response.
        # If msg_idx is the AI's message, then history should be up to msg_idx (exclusive).
        self.conversation_history = self.conversation_history[:msg_idx]

        # 2. Truncate UI - Remove old AI message and subsequent messages from UI
        # msg_idx is the index in the chat_frame.winfo_children() list
        self._clear_chat_from_index(msg_idx)

        # 3. Trigger new AI response
        if self.model_selector.cget("state") == "disabled":
            self._update_status("Cannot regenerate: No model selected or connection error.")
            self.is_generating = False
            self._toggle_input(True)
            return

        # Add AI message placeholder
        ai_label = self._add_message("assistant", "●●●", is_streaming=True)

        # History for AI is the now-truncated self.conversation_history
        # This history should contain the user message that prompted the original AI response.
        history_for_ai = self.conversation_history.copy()

        if not history_for_ai or history_for_ai[-1]['role'] != 'user':
            # This case should ideally not be reached if msg_idx > 0 and history was user, ai, user, ai ...
            # However, as a safeguard:
            self._update_status("Error: Invalid history state for regeneration.")
            self.is_generating = False
            self._toggle_input(True)
            # Clean up the placeholder message
            if ai_label and ai_label.master and ai_label.master.master:
                ai_label.master.master.destroy()
            return

        threading.Thread(
            target=self._stream_response,
            args=(history_for_ai, ai_label), # _stream_response appends the new AI response
            daemon=True
        ).start()

        self.after(100, self._scroll_to_bottom)


    def _cancel_edit(self, msg_idx, bubble_widget, original_bubble_children, original_content):
        """Cancel editing and restore original message."""
        # Clear editing UI (textbox, Save/Cancel buttons)
        for widget in bubble_widget.winfo_children():
            if widget not in original_bubble_children:
                widget.destroy()

        # Restore original children by repacking them
        for child_widget in original_bubble_children:
            if isinstance(child_widget, ctk.CTkLabel):
                child_widget.configure(text=original_content)
                child_widget.pack(padx=18, pady=12, anchor="w")
            elif isinstance(child_widget, ctk.CTkFrame):
                child_widget.pack(fill="x", padx=10, pady=(0, 5))
            else:
                child_widget.pack()
        
        # Restore the original controls frame that was hidden
        vertical_stack = bubble_widget.master
        if len(vertical_stack.winfo_children()) > 1:
            controls_frame = vertical_stack.winfo_children()[1]
            controls_frame.pack(fill="x", padx=5, pady=(2, 0)) # Re-pack it

        self._toggle_input(True) # Re-enable main input
        self.after(100, self._scroll_to_bottom)


if __name__ == "__main__":
    app = OllamaGuiApp()
    app.mainloop()