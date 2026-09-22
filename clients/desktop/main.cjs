/**
 * Phone-shaped window around the shared player.
 * The stream protocol lives in @strlix/stream-client, not in this file.
 * A future WebRTC build keeps this shell and swaps the transport.
 */
const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");

const player = path.join(__dirname, "..", "player", "www", "index.html");

function createWindow() {
  const win = new BrowserWindow({
    width: 420,
    height: 920,
    minWidth: 320,
    minHeight: 640,
    backgroundColor: "#000000",
    title: "Strlix",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  });
  win.loadFile(player, { query: { platform: "desktop", input: "cursor" } });
  ipcMain.removeHandler("toggle-fullscreen");
  ipcMain.handle("toggle-fullscreen", () => {
    win.setFullScreen(!win.isFullScreen());
    return win.isFullScreen();
  });
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => app.quit());
