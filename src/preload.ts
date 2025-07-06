import { contextBridge, ipcRenderer } from 'electron';

// Only expose a safe subset of ipcRenderer functionality if needed.
// For now, we can start with a basic example or leave it empty
// if no direct IPC calls from renderer to main are immediately required
// without specific handlers.

contextBridge.exposeInMainWorld('electronAPI', {
  // Example: expose a function to send a message and receive a response
  invoke: (channel: string, ...args: any[]) => ipcRenderer.invoke(channel, ...args),
  // Example: expose a function to subscribe to a channel
  on: (channel: string, listener: (event: Electron.IpcRendererEvent, ...args: any[]) => void) => {
    ipcRenderer.on(channel, listener);
    // Return a function to unsubscribe
    return () => ipcRenderer.removeListener(channel, listener);
  },
  // Add other specific IPC functions you want to expose here
});

console.log('Preload script loaded.');
