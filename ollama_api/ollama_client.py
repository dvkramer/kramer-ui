import requests
import json
import threading

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.current_stream_stop_event = None

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}/api/{endpoint}"
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()  # Raise an exception for HTTP errors
            if response.content:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    return response.json()
                # Handle cases like /api/delete which might not return JSON on success
                # or streaming endpoints before JSON parsing per line.
                # If not JSON, return as text. This might be an error page or unexpected format.
                return response.text
            return None # For successful requests with no content (e.g., DELETE)
        except requests.exceptions.RequestException as e:
            error_message = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None and e.response.content:
                try:
                    error_detail = e.response.json()
                    error_message += f" - {error_detail.get('error', e.response.text)}"
                except json.JSONDecodeError:
                    error_message += f" - {e.response.text}"
            print(error_message) # Or log this
            raise  # Re-raise the exception so the caller can handle it

    def check_connection(self):
        """Checks if the Ollama server is reachable."""
        try:
            # /api/tags is a lightweight GET request suitable for a health check.
            self._request("GET", "tags")
            return True, "Ollama server is responsive."
        except requests.exceptions.RequestException as e:
            return False, f"Ollama server not reachable: {e}"

    def list_models(self):
        """Lists all locally available models. (/api/tags)"""
        return self._request("GET", "tags")

    def stream_chat(self, model: str, messages: list, options: dict = None,
                    on_chunk: callable = None, on_complete: callable = None, on_error: callable = None):
        """
        Generates the next message in a chat conversation with streaming responses. (/api/chat)

        Args:
            model: The model name.
            messages: A list of message objects (e.g., [{"role": "user", "content": "..."}]).
            options: Optional dictionary of model parameters.
            on_chunk: Callback function for each received content chunk.
                      Receives the content string.
            on_complete: Callback function when the stream is done.
                         Receives the final JSON data object from Ollama.
            on_error: Callback function for stream errors.
                      Receives the exception.
        Returns:
            A threading.Event object that can be used to signal the stream to stop.
        """
        url = f"{self.base_url}/api/chat"
        payload = {"model": model, "messages": messages}
        if options:
            payload["options"] = options

        # For stopping the stream externally
        self.current_stream_stop_event = threading.Event()

        def stream_worker():
            try:
                with requests.post(url, json=payload, stream=True) as response:
                    response.raise_for_status()
                    buffer = ""
                    for line_bytes in response.iter_lines():
                        if self.current_stream_stop_event and self.current_stream_stop_event.is_set():
                            print("Stream stopped by caller.")
                            break
                        if line_bytes:
                            buffer += line_bytes.decode('utf-8')
                            # Ollama streams JSON objects separated by newlines
                            try:
                                data = json.loads(buffer)
                                buffer = "" # Reset buffer after successful parse

                                if self.current_stream_stop_event and self.current_stream_stop_event.is_set():
                                    print("Stream stopped by caller after parsing a chunk.")
                                    break

                                if data.get("done"):
                                    if on_complete:
                                        on_complete(data)
                                    break
                                if data.get("message", {}).get("content"):
                                    if on_chunk:
                                        on_chunk(data["message"]["content"])
                            except json.JSONDecodeError:
                                # Incomplete JSON object, wait for more data
                                # This happens if a line_bytes doesn't contain a full JSON object
                                # or if multiple JSON objects are in line_bytes (iter_lines should handle per line)
                                # For Ollama, each line IS a JSON object. If parse fails, it's likely an error or bad data.
                                # However, let's assume it could be a chunk of a larger JSON (though not typical for Ollama stream)
                                # A more robust way: split buffer by \n and try to parse each part.
                                lines = buffer.split('\n')
                                buffer = lines.pop() # Keep incomplete line in buffer
                                for single_line in lines:
                                    if single_line.strip():
                                        try:
                                            data = json.loads(single_line)
                                            if data.get("done"):
                                                if on_complete: on_complete(data)
                                                return # Exit worker as stream is done
                                            if data.get("message", {}).get("content") is not None: # Allow empty string content
                                                if on_chunk: on_chunk(data["message"]["content"])
                                        except json.JSONDecodeError as e_parse:
                                            print(f"Error parsing JSON line: {single_line}, Error: {e_parse}")
                                            # If a line fails to parse, it might be a genuine error from server
                                            # or an incomplete stream. For now, print and continue with buffer.
                                            # If it was a real JSON object that failed, buffer might get corrupted.
                                            # Ollama guarantees each line is a self-contained JSON.
                                            # So if json.loads(line_bytes.decode) failed, that line is problematic.
                                            # The current buffer logic is more for when iter_lines gives partial JSONs.
                                            # Let's simplify back to assuming each iter_lines() call gives one JSON doc or part of one.
                                            # The initial simpler approach of json.loads(buffer) after each line is usually fine.
                                            # Reverting to a slightly adjusted simpler logic:
                                            pass # Handled by the outer try-except for the whole buffer

                    # If buffer has content after loop (e.g. stream ended without newline)
                    if buffer.strip() and not (self.current_stream_stop_event and self.current_stream_stop_event.is_set()):
                        try:
                            data = json.loads(buffer)
                            if data.get("done"):
                                if on_complete: on_complete(data)
                            # It's unlikely to get a content chunk here if "done" wasn't true
                        except json.JSONDecodeError as e:
                            print(f"Error parsing final buffer content: {buffer}, Error: {e}")
                            if on_error: on_error(e)


            except requests.exceptions.RequestException as e:
                error_message = f"Stream request failed: {e}"
                if hasattr(e, 'response') and e.response is not None and e.response.content:
                    try:
                        error_detail = e.response.json()
                        error_message += f" - {error_detail.get('error', e.response.text)}"
                    except json.JSONDecodeError:
                         error_message += f" - {e.response.text}"
                print(error_message)
                if on_error:
                    on_error(e)
            except Exception as e: # Catch any other errors within the thread
                print(f"Unexpected error in stream worker: {e}")
                if on_error:
                    on_error(e)
            finally:
                if self.current_stream_stop_event and self.current_stream_stop_event.is_set():
                    print("Stream worker finished due to stop signal.")
                else:
                    print("Stream worker finished.")
                # Ensure on_complete is called if not already and no error occurred that on_error would handle
                # This might be complex if on_complete relies on the 'done' message. Best to let 'done' trigger it.

        thread = threading.Thread(target=stream_worker)
        thread.daemon = True # Allow main program to exit even if thread is running
        thread.start()
        return self.current_stream_stop_event

    def stop_current_stream(self):
        if self.current_stream_stop_event:
            self.current_stream_stop_event.set()
            print("Stop signal sent to current stream.")

    def pull_model(self, model_name: str, on_status: callable = None, on_progress: callable = None, on_complete: callable = None, on_error: callable = None):
        """
        Downloads a model from Ollama's registry with streaming progress. (/api/pull)
        Args:
            model_name: The name of the model to pull.
            on_status: Callback for general status updates (e.g., "pulling manifest"). Receives status string.
            on_progress: Callback for download progress. Receives (digest, total, completed).
            on_complete: Callback when pull is successful. Receives "success" status string.
            on_error: Callback for errors during pull. Receives exception or error message.
        Returns:
            A threading.Event object that can be used to signal the stream to stop.
        """
        url = f"{self.base_url}/api/pull"
        payload = {"model": model_name}

        self.current_stream_stop_event = threading.Event()

        def pull_worker():
            try:
                with requests.post(url, json=payload, stream=True) as response:
                    response.raise_for_status()
                    for line_bytes in response.iter_lines():
                        if self.current_stream_stop_event and self.current_stream_stop_event.is_set():
                            print("Pull stream stopped by caller.")
                            break
                        if line_bytes:
                            line = line_bytes.decode('utf-8')
                            try:
                                data = json.loads(line)
                                status = data.get("status")
                                if "error" in data:
                                    if on_error: on_error(data["error"])
                                    return

                                if "digest" in data and "total" in data and "completed" in data:
                                    if on_progress:
                                        on_progress(data["digest"], data["total"], data["completed"])
                                elif status == "success":
                                    if on_complete:
                                        on_complete(status)
                                    return # Successfully completed
                                elif status:
                                    if on_status:
                                        on_status(status)
                            except json.JSONDecodeError as e:
                                print(f"Error parsing pull stream line: {line}, Error: {e}")
                                # Potentially an error message not in JSON format or incomplete stream
                                if on_error: on_error(f"Failed to parse progress line: {line}")
            except requests.exceptions.RequestException as e:
                error_message = f"Pull model request failed: {e}"
                # (Error message construction similar to _request method)
                print(error_message)
                if on_error: on_error(e)
            except Exception as e:
                print(f"Unexpected error in pull_worker: {e}")
                if on_error: on_error(e)
            finally:
                print("Pull worker finished.")

        thread = threading.Thread(target=pull_worker)
        thread.daemon = True
        thread.start()
        return self.current_stream_stop_event


    def delete_model(self, model_name: str):
        """Removes a model from the local machine. (/api/delete)"""
        payload = {"model": model_name}
        return self._request("DELETE", "delete", json=payload)

    def show_model_info(self, model_name: str):
        """Gets detailed information about a specific model. (/api/show)"""
        payload = {"model": model_name}
        return self._request("POST", "show", json=payload)

    def list_running_models(self):
        """Lists currently loaded models in memory. (/api/ps)"""
        return self._request("GET", "ps")


if __name__ == '__main__':
    import time
    client = OllamaClient()

    print("Checking Ollama connection...")
    connected, message = client.check_connection()
    print(f"Connection status: {connected} - {message}")

    if not connected:
        print("Cannot run further tests without a running Ollama server.")
        exit()

    print("\nListing local models...")
    try:
        models_data = client.list_models()
        if models_data and "models" in models_data:
            print("Available models:")
            for model in models_data["models"]:
                print(f"  - {model['name']} (Size: {model['size']})")
            if not models_data["models"]:
                print("  No local models found. Consider pulling one, e.g., 'phi3'.")

                # Test pulling a model if none exist (e.g. phi3:mini)
                # Be careful with large models for automated tests.
                # For now, this part is manual if you want to test pull.
                # print("\nTesting model pull (phi3:mini)...")
                # def pull_status(s): print(f"Pull status: {s}")
                # def pull_progress(d, t, c): print(f"Pull progress: Digest {d[:12]} - {c}/{t}")
                # def pull_complete(s): print(f"Pull complete: {s}")
                # def pull_error(e): print(f"Pull error: {e}")
                # pull_event = client.pull_model("phi3:mini", on_status=pull_status, on_progress=pull_progress, on_complete=pull_complete, on_error=pull_error)
                # while not pull_event.is_set() and any(t.name == "Thread-2" for t in threading.enumerate()): # Thread-2 is an example name
                #     try:
                #         active_threads = [t for t in threading.enumerate() if t.name.startswith("Thread-") and t.is_alive()]
                #         # Find the pull worker thread specifically if possible, or just wait generally
                #         pull_worker_alive = False
                #         for t in active_threads:
                #             if "pull_worker" in str(t._target): # A bit hacky way to identify
                #                 pull_worker_alive = True
                #                 break
                #         if not pull_worker_alive and not pull_event.is_set(): # Thread finished but event not set (e.g. error)
                #             print("Pull worker seems to have finished or not started correctly.")
                #             break
                #         time.sleep(1)
                #     except KeyboardInterrupt:
                #         print("Pull test interrupted. Stopping stream...")
                #         client.stop_current_stream()
                #         break
                # print("Pull test finished or interrupted.")
                # models_data = client.list_models() # Refresh models list
        else:
            print("Could not parse model list response.")

    except requests.exceptions.RequestException as e:
        print(f"Error listing models: {e}")

    # Proceed with chat only if there are models
    if models_data and models_data.get("models"):
        test_model_name = models_data["models"][0]["name"] # Use the first available model
        print(f"\nTesting chat streaming with model: {test_model_name}...")

        # Use a dictionary to store test results to avoid nonlocal issues in callbacks
        test_results = {
            "chat_chunks": [],
            "chat_completed_data": None,
            "chat_error_occurred": None,
            "chat_done_event": threading.Event()
        }

        def on_chat_chunk(chunk):
            print(f"Chunk: '{chunk}'", end='', flush=True)
            test_results["chat_chunks"].append(chunk)

        def on_chat_complete(data):
            print("\nChat stream complete!")
            test_results["chat_completed_data"] = data
            # print(f"Full completion data: {data}")
            test_results["chat_done_event"].set()

        def on_chat_error(error):
            print(f"\nChat stream error: {error}")
            test_results["chat_error_occurred"] = error
            test_results["chat_done_event"].set()

        messages = [{"role": "user", "content": "Hello! Briefly tell me about yourself."}]

        print(f"Sending messages to {test_model_name}: {messages}")
        stop_event = client.stream_chat(
            test_model_name,
            messages,
            on_chunk=on_chat_chunk,
            on_complete=on_chat_complete,
            on_error=on_chat_error
        )

        # Wait for chat to complete or timeout
        print("\nWaiting for chat response (max 30s, Ctrl+C to stop early)...")
        test_results["chat_done_event"].wait(timeout=30)

        if not test_results["chat_done_event"].is_set():
            print("\nChat timeout or still running. Attempting to stop stream...")
            client.stop_current_stream()
            test_results["chat_done_event"].wait(timeout=5) # Wait a bit more for it to stop

        if test_results["chat_error_occurred"]:
            print(f"Chat test failed with error: {test_results['chat_error_occurred']}")
        elif test_results["chat_completed_data"]:
            print(f"Chat test successful. Full response: {''.join(test_results['chat_chunks'])}")
            print(f"Done reason: {test_results['chat_completed_data'].get('done_reason')}")
        else:
            print("Chat test did not complete as expected.")

        # Test showing model info
        print(f"\nShowing info for model: {test_model_name}")
        try:
            info = client.show_model_info(test_model_name)
            if info: print(f"Model info (first 100 chars of modelfile): {info.get('modelfile', '')[:100]}...")
        except requests.exceptions.RequestException as e:
            print(f"Error showing model info: {e}")

        # Test listing running models (usually empty unless a model is kept alive)
        print("\nListing running models (models in memory):")
        try:
            running_models = client.list_running_models()
            if running_models and "models" in running_models:
                if running_models["models"]:
                    for model in running_models["models"]:
                        print(f"  - {model['name']}")
                else:
                    print("  No models currently loaded in memory (this is normal).")
        except requests.exceptions.RequestException as e:
            print(f"Error listing running models: {e}")

        # Test deleting a model (use with caution, or pull a small test model first)
        # For this example, we won't delete the model used for chat to keep test simple.
        # If you pulled 'phi3:mini' for testing, you could delete it here.
        # Example:
        # print("\nTesting model delete (phi3:mini)...")
        # try:
        #   client.delete_model("phi3:mini")
        #   print("phi3:mini deleted successfully (if it existed).")
        # except requests.exceptions.RequestException as e:
        #   if e.response is not None and e.response.status_code == 404:
        #       print("phi3:mini not found, so not deleted.")
        #   else:
        #       print(f"Error deleting model phi3:mini: {e}")

    else:
        print("\nSkipping chat and model info tests as no local models are available.")

    print("\nOllamaClient tests finished.")
