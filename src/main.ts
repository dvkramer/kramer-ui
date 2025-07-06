import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import isDev from 'electron-is-dev';

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // We'll create this later if needed for secure IPC
      nodeIntegration: false, // Best practice for security
      contextIsolation: true, // Best practice for security
      devTools: isDev, // Use isDev to control DevTools
    },
  });

  if (isDev) {
    // When using webpack-dev-server, HtmlWebpackPlugin serves index.html at the root of devServer.publicPath or output.publicPath
    // Assuming dev server runs on port 8080 and serves content from 'dist/renderer' at its root.
    mainWindow.loadURL('http://localhost:8080/index.html');
    mainWindow.webContents.openDevTools();
  } else {
    // In production, load the bundled HTML file.
    // The path will be dist/renderer/index.html relative to the app root.
    const rendererIndexPath = path.join(__dirname, 'renderer', 'index.html');
    mainWindow.loadFile(rendererIndexPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Example IPC handler (optional, expand as needed)
ipcMain.handle('some-async-action', async (event, ...args) => {
  // Do something asynchronous
  console.log('IPC Main received:', args);
  return { reply: 'pong' };
});

// Make sure to adjust webpack.config.js if you add a preload script.
// It would need its own entry point and target.
// For now, we'll assume no preload script or create a dummy one if renderer complains.

// Add a dummy preload.js for now to satisfy the webPreferences
// We will need to tell webpack to copy/bundle this too.
// For simplicity, let's update webpack.config.js to copy it.
// And create the dummy preload.js file.
