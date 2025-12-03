import { app, BrowserWindow, ipcMain } from "electron";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "fs";
const __dirname$1 = path.dirname(fileURLToPath(import.meta.url));
let pythonProcess = null;
process.env.APP_ROOT = path.join(__dirname$1, "..");
const VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];
const MAIN_DIST = path.join(process.env.APP_ROOT, "dist-electron");
const RENDERER_DIST = path.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, "public") : RENDERER_DIST;
let win;
function createWindow() {
  win = new BrowserWindow({
    icon: path.join(process.env.VITE_PUBLIC, "electron-vite.svg"),
    autoHideMenuBar: true,
    width: 1280,
    height: 800,
    titleBarStyle: "hidden",
    titleBarOverlay: {
      color: "#040508",
      // 自定义标题栏颜色
      symbolColor: "#F5F5F5"
      // 控制按钮颜色
    },
    webPreferences: {
      preload: path.join(__dirname$1, "preload.mjs")
    },
    minWidth: 1280,
    minHeight: 800
  });
  win.webContents.on("did-finish-load", () => {
    win == null ? void 0 : win.webContents.send("main-process-message", (/* @__PURE__ */ new Date()).toLocaleString());
  });
  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(RENDERER_DIST, "index.html"));
  }
  win.on("closed", () => {
    if (pythonProcess && !pythonProcess.killed) {
      pythonProcess.kill("SIGTERM");
    }
    win = null;
  });
  ipcMain.on("set-theme", (_, theme) => {
    if (win) {
      if (theme === "dark") {
        win.setTitleBarOverlay({
          color: "#252525",
          // 暗色主题的颜色
          symbolColor: "#CCCCCC"
          // 暗色主题的符号颜色
        });
      } else {
        win.setTitleBarOverlay({
          color: "white",
          // 亮色主题的颜色
          symbolColor: "#3D3D3D"
          // 亮色主题的符号颜色
        });
      }
    }
  });
}
function startPythonBackend() {
  const isPackaged = app.isPackaged;
  const resourcesPath = isPackaged ? process.resourcesPath : path.join(__dirname$1, "..");
  const pythonExePath = path.join(
    resourcesPath,
    isPackaged ? "backend/app.exe" : "src/backend/app.py"
    // 开发环境仍用 .py
  );
  if (!fs.existsSync(pythonExePath)) {
    console.error(`❌ Python 可执行文件不存在: ${pythonExePath}`);
    return;
  }
  const launchArgs = isPackaged ? [] : [pythonExePath];
  pythonProcess = spawn(
    isPackaged ? pythonExePath : "python",
    // 命令
    isPackaged ? launchArgs : [...launchArgs, "--debug=False"],
    { cwd: path.dirname(pythonExePath) }
    // 设置工作目录
  );
  pythonProcess.on("error", (err) => {
    console.error("Python进程启动失败:", err);
    win == null ? void 0 : win.webContents.send("python-error", err.message);
  });
  pythonProcess.stdout.on("data", (data) => console.log(`[Python] ${data.toString().trim()}`));
  pythonProcess.stderr.on("data", (data) => console.error(`[Python-ERR] ${data.toString().trim()}`));
}
app.on("window-all-closed", () => {
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill("SIGTERM");
  }
  if (process.platform !== "darwin") {
    app.quit();
    win = null;
  }
});
app.whenReady().then(() => {
  createWindow();
  startPythonBackend();
  app.on("will-quit", () => {
    if (pythonProcess && !pythonProcess.killed) {
      pythonProcess.kill("SIGTERM");
    }
  });
});
export {
  MAIN_DIST,
  RENDERER_DIST,
  VITE_DEV_SERVER_URL
};
