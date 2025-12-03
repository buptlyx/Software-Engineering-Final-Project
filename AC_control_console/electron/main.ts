import { app, BrowserWindow, ipcMain } from 'electron'
//import { createRequire } from 'node:module'
import {spawn} from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { ChildProcessWithoutNullStreams } from 'child_process'

//const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))
let pythonProcess: ChildProcessWithoutNullStreams | null = null

// The built directory structure
//
// ├─┬─┬ dist
// │ │ └── index.html
// │ │
// │ ├─┬ dist-electron
// │ │ ├── main.js
// │ │ └── preload.mjs
// │
process.env.APP_ROOT = path.join(__dirname, '..')

// 🚧 Use ['ENV_NAME'] avoid vite:define plugin - Vite@2.x
export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, 'public') : RENDERER_DIST

let win: BrowserWindow | null

function createWindow() {
  win = new BrowserWindow({
    icon: path.join(process.env.VITE_PUBLIC, 'electron-vite.svg'),
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
      preload: path.join(__dirname, 'preload.mjs'),
    },
    minWidth: 1280,
    minHeight: 800,
  })

  // Test active push message to Renderer-process.
  win.webContents.on('did-finish-load', () => {
    win?.webContents.send('main-process-message', (new Date).toLocaleString())
  })

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL)
  } else {
    // win.loadFile('dist/index.html')
    win.loadFile(path.join(RENDERER_DIST, 'index.html'))
  }


  // Quit when all windows are closed, except on macOS. There, it's common
  // for applications and their menu bar to stay active until the user quits
  // explicitly with Cmd + Q.
  win.on('closed', () => {
      // 终止Python进程
      if (pythonProcess && !pythonProcess.killed) {
        pythonProcess.kill('SIGTERM');
      }
      win = null;
    })

  // 监听来自渲染进程的 title bar overlay 更新请求
  ipcMain.on('set-theme', (_, theme) => {
  if (win) {
    if (theme === 'dark') {
      win.setTitleBarOverlay({
        color: '#252525', // 暗色主题的颜色
        symbolColor: '#CCCCCC' // 暗色主题的符号颜色
      });
    } else {
      win.setTitleBarOverlay({
        color: 'white', // 亮色主题的颜色
        symbolColor: '#3D3D3D' // 亮色主题的符号颜色
      });
    }
  }
});
}

import fs from 'fs' 
function startPythonBackend() {
  const isPackaged = app.isPackaged;
  const resourcesPath = isPackaged 
    ? process.resourcesPath 
    : path.join(__dirname, '..'); 

  const pythonExePath = path.join(
    resourcesPath,
    isPackaged ? 'backend/app.exe' : 'src/backend/app.py' // 开发环境仍用 .py
  );

  if (!fs.existsSync(pythonExePath)) {
    console.error(`❌ Python 可执行文件不存在: ${pythonExePath}`);
    return;
  }

  const launchArgs = isPackaged 
    ? [] 
    : [pythonExePath]; 

  pythonProcess = spawn(
    isPackaged ? pythonExePath : 'python', // 命令
    isPackaged ? launchArgs : [...launchArgs, '--debug=False'],
    { cwd: path.dirname(pythonExePath) } // 设置工作目录
  );

  pythonProcess.on('error', (err) => {
    console.error('Python进程启动失败:', err);
    win?.webContents.send('python-error', err.message);
  });

  pythonProcess.stdout.on('data', (data) => 
    console.log(`[Python] ${data.toString().trim()}`));
  pythonProcess.stderr.on('data', (data) => 
    console.error(`[Python-ERR] ${data.toString().trim()}`));
}


// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  // 终止Python进程
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill('SIGTERM');
  }
  
  if (process.platform !== 'darwin') {
    app.quit()
    win = null
  }
})

// app.on('activate', () => {
//   // On OS X it's common to re-create a window in the app when the
//   // dock icon is clicked and there are no other windows open.
//   if (BrowserWindow.getAllWindows().length === 0) {
//     createWindow()
//   }
// })

app.whenReady().then(() => {
  createWindow();
  startPythonBackend(); // 启动 Python

  // 退出时终止 Python 进程（作为备用方案）
  app.on('will-quit', () => {
    if (pythonProcess && !pythonProcess.killed) {
      pythonProcess.kill('SIGTERM');
    }
  });
});