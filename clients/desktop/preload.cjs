const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("strlixDesktop", {
  platform: "desktop",
  toggleFullScreen: () => ipcRenderer.invoke("toggle-fullscreen"),
});
