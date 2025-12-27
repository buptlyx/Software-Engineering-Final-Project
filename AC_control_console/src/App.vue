<template>
  <div class="app-container">
    <!-- 拖动条 -->
    <div class="drag-bar"></div>
    
    <!-- 左侧导航：固定宽度 -->
    <SideBar 
      :current-tab="currentTab" 
      @update:tab="currentTab = $event" 
      class="app-sidebar"
      style="-webkit-app-region: no-drag;"
    />

    <!-- 右侧内容：弹性自适应 -->
    <main class="app-content">
      <!-- 顶部装饰条 -->
      <div class="top-bar">
        <span class="system-status" style="-webkit-app-region: no-drag;">
          <Circle :size="12" :fill="'currentColor'" style="margin-right: 8px;" />
          SYSTEM ONLINE
        </span>

      </div>

      <!-- 动态组件切换区 -->
      <div class="view-viewport">
        <transition name="fade-slide" mode="out-in">
          <component :is="currentViewComponent" />
        </transition>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Circle } from 'lucide-vue-next';
import SideBar from './components/sideBar.vue';
import CheckIn from './components/check_in.vue';
import UserConsole from './components/user_console.vue';
import Monitor from './components/monitor.vue';
import Report from './components/report.vue';

const currentTab = ref('check-in');

const currentViewComponent = computed(() => {
  const map = {
    'check-in': CheckIn,
    'user-console': UserConsole,
    'monitor': Monitor,
    'report': Report
  };
  return map[currentTab.value];
});
</script>

<style lang="scss">
/* --- 全局样式定义 --- */
:root {
  --primary: #00f2ff;         /* 赛博青 */
  --primary-dim: rgba(0, 242, 255, 0.1);
  --bg-dark: #0f0f13;         /* 深邃黑 */
  --panel-bg: rgba(30, 35, 48, 0.7); /* 玻璃面板背景 */
  --text-main: #ffffff;
  --text-sec: rgba(255, 255, 255, 0.5);
  --border: rgba(255, 255, 255, 0.1);
  --glass: blur(20px);
}

* { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }

body {
  background-color: var(--bg-dark);
  font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  color: var(--text-main);
  overflow: hidden; /* 防止整个页面滚动 */
}

/* --- 布局结构 --- */
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: radial-gradient(circle at 10% 10%, #1a1f2c 0%, #000 100%);
}

.app-sidebar {
  width: 15%;
  min-width: 60px;
  max-width: 300px;
  flex-shrink: 0;
  z-index: 10;
}

.app-content {
  flex: 1; /* 占据剩余空间 */
  display: flex;
  flex-direction: column;
  padding: 0;
  position: relative;
  overflow: hidden;
}
.app-sidebar {
  z-index: 10;
}
.drag-bar {
  height: 30px;
  width: 100%;
  position: absolute;
  -webkit-app-region: drag;
  background: transparent;
  top: 0;
  left: 0;
  z-index: 100;
}

.view-viewport {
  flex: 1;
  padding: 30px;
  overflow: visible;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  z-index: 1;
}
.top-bar {
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  letter-spacing: 2px;
  color: var(--text-sec);
  position: relative;
  z-index: 10;

  .system-status { color: var(--primary); text-shadow: 0 0 5px var(--primary); }
}

.view-viewport {
  flex: 1;
  padding: 30px;
  overflow: hidden; /* 内部面板自己处理滚动 */
  display: flex;
  justify-content: center;
  align-items: center;
}

/* --- 动画 --- */
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.3s ease;
}
.fade-slide-enter-from { opacity: 0; transform: translateY(10px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }

/* --- 滚动条美化 --- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
::-webkit-scrollbar-track { background: transparent; }
</style>