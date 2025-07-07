import customtkinter as ctk
import ollama
from ollama import Client
import threading
import json
from datetime import datetime

# --- Constants ---
APP_NAME = "Ollama Chat"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
OLLAMA_HOST = 'http://127.0.0.1:11434'

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
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
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
            text="🦙 Ollama Chat", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text']
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Model selector
        model_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        model_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        model_label = ctk.CTkLabel(
            model_frame, 
            text="Model:", 
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_muted']
        )
        model_label.grid(row=0, column=0, padx=(0, 10))
        
        self.model_selector = ctk.CTkOptionMenu(
            model_frame,
            variable=self.selected_model,
            values=["Loading..."],
            state="disabled",
            width=200,
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
            font=ctk.CTkFont(size=12)
        )
        self.new_chat_btn.grid(row=0, column=2, padx=(15, 0))
    
    def _create_chat_area(self):
        """Create scrollable chat area"""
        self.chat_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=COLORS['bg'],
            scrollbar_button_color=COLORS['surface_light'],
            scrollbar_button_hover_color=COLORS['accent']
        )
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.chat_frame.grid_columnconfigure(0, weight=1)
    
    def _create_input_area(self):
        """Create input area with text box and send button"""
        self.input_frame = ctk.CTkFrame(
            self,
            height=80,
            corner_radius=15,
            fg_color=COLORS['surface']
        )
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Input text box
        self.user_input = ctk.CTkTextbox(
            self.input_frame,
            height=40,
            corner_radius=10,
            fg_color=COLORS['surface_light'],
            border_color=COLORS['surface_light'],
            font=ctk.CTkFont(size=12)
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
            font=ctk.CTkFont(size=12, weight="bold")
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
        self.status_frame.grid(row=3, column=0, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text=f"Connecting to {OLLAMA_HOST}...",
            font=ctk.CTkFont(size=10),
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
    
    def _add_message(self, role, content, is_streaming=False):
        """Add a message bubble to the chat"""
        # Create message container
        msg_container = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        msg_container.grid(row=len(self.chat_frame.winfo_children()), column=0, sticky="ew", pady=5)
        msg_container.grid_columnconfigure(0, weight=1)
        
        # Configure alignment and colors
        if role == "user":
            anchor = "right"
            bg_color = COLORS['user_bubble']
            text_color = "white"
        else:
            anchor = "left"
            bg_color = COLORS['ai_bubble']
            text_color = COLORS['text']
        
        # Create message bubble
        bubble = ctk.CTkFrame(
            msg_container,
            fg_color=bg_color,
            corner_radius=15
        )
        bubble.pack(side=anchor, padx=10, fill="x" if role == "assistant" else "none", expand=True if role == "assistant" else False)
        
        # Add message content
        message_label = ctk.CTkLabel(
            bubble,
            text=content,
            font=ctk.CTkFont(size=12),
            text_color=text_color,
            wraplength=600,
            justify="left"
        )
        message_label.pack(padx=15, pady=10, anchor="w")
        
        # Add timestamp for completed messages
        if not is_streaming:
            timestamp = datetime.now().strftime("%H:%M")
            time_label = ctk.CTkLabel(
                msg_container,
                text=timestamp,
                font=ctk.CTkFont(size=9),
                text_color=COLORS['text_muted']
            )
            time_label.pack(side=anchor, padx=15, pady=(0, 5))
        
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
                    self.after(0, lambda: ai_label.configure(text=full_response))
                    self.after(0, self._scroll_to_bottom)
            
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
        """Toggle input widgets"""
        state = "normal" if enabled else "disabled"
        self.user_input.configure(state=state)
        self.send_button.configure(state=state)
        
        if enabled:
            self.user_input.focus()
    
    def _new_chat(self):
        """Start a new chat"""
        self.conversation_history.clear()
        
        # Clear chat area
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        
        self._update_status("New chat started")
        self.user_input.focus()

if __name__ == "__main__":
    app = OllamaGuiApp()
    app.mainloop()