# 分布式温控系统 (AC Control Console)

本项目是一个基于 Vue 3 + Electron + Python (Flask) 的分布式温控系统控制台。系统模拟了酒店房间的空调控制、计费和调度逻辑。

## 核心对象实现说明

本项目后端逻辑主要集中在 `src/backend/` 目录下，核心业务逻辑由以下三个主要对象构成：

### 1. 调度对象 (Scheduler Object)

调度对象负责管理所有房间的空调服务请求，决定哪些房间可以获得服务（供暖/制冷），哪些房间需要等待。

*   **实现类**: `Scheduler`
*   **文件位置**: [`src/backend/app.py`](src/backend/app.py)
*   **主要职责**:
    *   **队列管理**: 维护服务队列 (`service_queue`) 和等待队列 (`waiting_queue`)。
    *   **调度策略**: 实现了基于风速优先级的调度算法。高风速请求优先于低风速请求。
    *   **时间片轮转**: 实现了等待队列的时间片机制，防止低优先级请求长期得不到服务。
    *   **抢占机制**: 当服务队列已满且有更高优先级的等待请求时，执行抢占逻辑 (`preempt_service`)。

### 2. 服务对象 (Service Object)

服务对象代表具体的房间实体，是接受调度和服务的单元。

*   **实现类**: `Room`
*   **文件位置**: [`src/backend/app.py`](src/backend/app.py)
*   **主要职责**:
    *   **状态维护**: 维护房间的当前温度、目标温度、风速、电源状态等。
    *   **计费逻辑**: `update_temp_and_fee` 方法根据当前风速和费率计算费用，并更新温度。
    *   **租户信息**: 存储当前入住的租户信息（ID、姓名、入住天数等）。
    *   **模拟环境**: 模拟房间温度随时间的自然回升或下降 (`_handle_return_temp`)。

### 3. 详单对象 (Detail Record Object)

详单对象用于持久化存储每一次空调服务会话的详细信息，用于后续的报表生成和账单查询。

*   **实现方式**: 数据库表 `ac_sessions` 及相关操作函数
*   **文件位置**: 
    *   数据库操作: [`src/backend/database.py`](src/backend/database.py)
    *   生成逻辑: [`src/backend/app.py`](src/backend/app.py)
*   **主要职责**:
    *   **数据存储**: 在 SQLite 数据库的 `ac_sessions` 表中存储记录。
    *   **记录内容**: 包含房间号、请求时间、开始时间、结束时间、服务时长、风速、本次费用等。
    *   **生成时机**: 当房间停止空调服务（关机或被抢占）或更改风速时，系统会调用 `database.log_ac_session` 生成一条详单记录。

## 项目结构概览

```
AC_control_console/
├── src/
│   ├── backend/           # 后端核心逻辑
│   │   ├── app.py         # 主程序，包含 Scheduler 和 Room 类
│   │   └── database.py    # 数据库操作，包含详单(ac_sessions)管理
│   ├── components/        # 前端 Vue 组件
│   │   ├── monitor.vue    # 监控面板
│   │   ├── user_console.vue # 用户控制台
│   │   └── ...
│   └── ...
├── electron/              # Electron 主进程代码
└── ...
```

## 启动说明

1.  **后端**: 运行 `src/backend/app.py` 启动 Flask 服务器。
2.  **前端**: 运行 `npm run dev` (开发模式) 或构建 Electron 应用。
