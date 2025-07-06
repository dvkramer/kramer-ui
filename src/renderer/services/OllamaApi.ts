// Ollama API Service

export interface OllamaModelDetails {
  parent_model: string;
  format: string;
  family: string;
  families: string[] | null;
  parameter_size: string;
  quantization_level: string;
}

export interface OllamaModel {
  name: string;
  model: string; // Added: The full model name, e.g., "llama3:latest"
  modified_at: string;
  size: number;
  digest: string;
  details: OllamaModelDetails;
  // Added from /api/ps example, may or may not be present in /api/tags
  expires_at?: string;
}


export interface ListModelsResponse {
  models: OllamaModel[];
}

export interface OllamaMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  images?: string[];
}

export interface OllamaChatRequestBody {
  model: string;
  messages: OllamaMessage[];
  format?: 'json';
  options?: Record<string, any>;
  stream?: boolean;
  keep_alive?: string | number;
}

export interface OllamaChatStreamChunk {
  model: string;
  created_at: string;
  message?: OllamaMessage;
  done: boolean;
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
  done_reason?: string;
}

export interface ShowModelInfoResponse {
  license?: string;
  modelfile?: string;
  parameters?: string;
  template?: string;
  system?: string;
  details: OllamaModelDetails;
  modified_at: string;
}

export interface PullModelStatus {
  status: string;
  digest?: string;
  total?: number;
  completed?: number;
  error?: string;
}

// For /api/generate endpoint (non-chat completion)
export interface OllamaGenerateRequestBody {
  model: string;
  prompt: string;
  images?: string[]; // if model supports multimodal
  format?: 'json';
  options?: Record<string, any>;
  system?: string; // System prompt
  template?: string; // Full prompt template
  context?: number[]; // Previous context
  stream?: boolean;
  raw?: boolean; // Use raw prompt without templating
  keep_alive?: string | number;
}

export interface OllamaGenerateStreamChunk {
  model: string;
  created_at: string;
  response: string; // The generated text chunk
  done: boolean;
  context?: number[]; // Context for next generation (if done)
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
  done_reason?: string;
}


class OllamaApi {
  private baseUrl: string;
  private currentChatController: AbortController | null = null;
  private currentPullController: AbortController | null = null;
  private currentGenerateController: AbortController | null = null;


  constructor(baseUrl: string = 'http://localhost:11434') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    if (!response.ok) {
      let errorBody;
      try {
        errorBody = await response.json();
      } catch (e) {
        errorBody = { error: `HTTP error! status: ${response.status} ${response.statusText}`, status: response.status };
      }
      if (!errorBody.error) { // Ensure there's an error message
        errorBody.error = `HTTP error! status: ${response.status} ${response.statusText}`;
      }
      if (!errorBody.status) {
        errorBody.status = response.status;
      }
      throw errorBody;
    }
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T;
    }
    return response.json() as Promise<T>;
  }

  async listModels(): Promise<ListModelsResponse> {
    return this.request<ListModelsResponse>('/api/tags');
  }

  async checkConnection(): Promise<boolean> {
    try {
      // /api/tags is good, or just / to see if server is up.
      // Ollama root returns "Ollama is running" as plain text.
      const res = await fetch(`${this.baseUrl}/`, { method: 'GET', signal: AbortSignal.timeout(3000) });
      return res.ok;
    } catch (error) {
      console.warn('Ollama connection check failed:', error);
      return false;
    }
  }

  async *streamChat(
    body: OllamaChatRequestBody
  ): AsyncGenerator<OllamaChatStreamChunk, void, undefined> {
    if (this.currentChatController) {
      this.currentChatController.abort('New chat request started');
    }
    this.currentChatController = new AbortController();
    const requestBody = { ...body, stream: body.stream !== undefined ? body.stream : true };

    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: this.currentChatController.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status} ${response.statusText}`, status: response.status }));
        if (!errorData.error) errorData.error = `HTTP error! status: ${response.status} ${response.statusText}`;
        if (!errorData.status) errorData.status = response.status;
        throw errorData;
      }
      if (!response.body) throw new Error('Response body is null for chat stream');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            try { yield JSON.parse(buffer.trim()); }
            catch (e: any) { console.error('Failed to parse final JSON chunk (chat):', buffer, e.message); throw new Error(`Parse final JSON (chat): ${e.message}`); }
          }
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.trim()) {
            try { yield JSON.parse(line); }
            catch (e: any) { console.error('Failed to parse JSON stream line (chat):', line, e.message); throw new Error(`Parse stream line (chat): ${e.message}`); }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') { console.log('Chat stream aborted'); return; }
      console.error('Error in streamChat:', error); throw error;
    } finally {
      this.currentChatController = null;
    }
  }

  stopStreamingChat() {
    if (this.currentChatController) {
      this.currentChatController.abort('User requested stop chat');
      this.currentChatController = null;
    }
  }

  async *streamGenerate(
    body: OllamaGenerateRequestBody
  ): AsyncGenerator<OllamaGenerateStreamChunk, void, undefined> {
    if (this.currentGenerateController) {
      this.currentGenerateController.abort('New generate request started');
    }
    this.currentGenerateController = new AbortController();
    const requestBody = { ...body, stream: body.stream !== undefined ? body.stream : true };

    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: this.currentGenerateController.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status} ${response.statusText}`, status: response.status }));
        if (!errorData.error) errorData.error = `HTTP error! status: ${response.status} ${response.statusText}`;
        if (!errorData.status) errorData.status = response.status;
        throw errorData;
      }
      if (!response.body) throw new Error('Response body is null for generate stream');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            try { yield JSON.parse(buffer.trim()); }
            catch (e: any) { console.error('Failed to parse final JSON chunk (gen):', buffer, e.message); throw new Error(`Parse final JSON (gen): ${e.message}`);}
          }
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.trim()) {
            try { yield JSON.parse(line); }
            catch (e: any) { console.error('Failed to parse JSON stream line (gen):', line, e.message); throw new Error(`Parse stream line (gen): ${e.message}`);}
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') { console.log('Generate stream aborted'); return; }
      console.error('Error in streamGenerate:', error); throw error;
    } finally {
      this.currentGenerateController = null;
    }
  }

  stopStreamingGenerate() {
    if (this.currentGenerateController) {
      this.currentGenerateController.abort('User requested stop generate');
      this.currentGenerateController = null;
    }
  }

  async *pullModel(
    modelName: string,
    insecure?: boolean
  ): AsyncGenerator<PullModelStatus, void, undefined> {
    if (this.currentPullController) {
      this.currentPullController.abort('New pull request started');
    }
    this.currentPullController = new AbortController();
    const body: { name: string; insecure?: boolean; stream?: boolean } = { name: modelName, stream: true };
    if (insecure) body.insecure = true;

    try {
      const response = await fetch(`${this.baseUrl}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: this.currentPullController.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status} ${response.statusText}`, status: response.status }));
        if (!errorData.error) errorData.error = `HTTP error! status: ${response.status} ${response.statusText}`;
        if (!errorData.status) errorData.status = response.status;
        throw errorData;
      }
      if (!response.body) throw new Error('Response body is null for pull model');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buffer.trim()) {
            try { yield JSON.parse(buffer.trim()); }
            catch (e: any) { console.error('Failed to parse final JSON chunk (pull):', buffer, e.message); }
          }
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.trim()) {
            try {
              const statusUpdate: PullModelStatus = JSON.parse(line);
              yield statusUpdate;
              if (statusUpdate.status === 'success' || statusUpdate.error) return;
            } catch (e: any) {
              console.error('Failed to parse JSON stream line (pull):', line, e.message);
              yield { status: 'error parsing line', error: e.message };
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') { console.log('Model pull aborted'); return; }
      console.error('Error in pullModel:', error);
      yield { status: 'error', error: (error as Error).message || 'Unknown pull error' };
      throw error;
    } finally {
      this.currentPullController = null;
    }
  }

  stopPullingModel() {
    if (this.currentPullController) {
      this.currentPullController.abort('User requested stop pulling model');
      this.currentPullController = null;
    }
  }

  async deleteModel(modelName: string): Promise<void> {
    return this.request<void>(`/api/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName }), // Using "model" as per prompt example
    });
  }

  async showModelInfo(modelName: string): Promise<ShowModelInfoResponse> {
    return this.request<ShowModelInfoResponse>(`/api/show`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName }), // Using "model" as per prompt example
    });
  }

  async listRunningModels(): Promise<{ models: OllamaModel[] }> {
    return this.request<{ models: OllamaModel[] }>(`/api/ps`);
  }
}

export const ollamaApi = new OllamaApi();
export type OllamaApiService = typeof ollamaApi;
