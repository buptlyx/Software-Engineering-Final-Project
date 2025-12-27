<template>
  <aside class="sidebar-glass" ref="sidebarRef" :class="{ 'narrow-mode': isNarrow }">
    <div class="logo-area">
      <div class="logo-icon">H</div>
      <div class="logo-text">HOTEL<br>SYSTEM</div>
    </div>

    <nav class="nav-menu">
      <div 
        v-for="tab in tabs" 
        :key="tab.id"
        class="nav-item"
        :class="{ active: currentTab === tab.id }"
        @click="$emit('update:tab', tab.id)"
        :title="isNarrow ? tab.label : ''"
      >
        <span class="icon">
          <LogIn v-if="tab.icon === 'log-in'" :size="20" />
          <LogOut v-if="tab.icon === 'log-out'" :size="20" />
          <Snowflake v-if="tab.icon === 'snowflake'" :size="20" />
          <square-activity v-if="tab.icon === 'SquareActivity'" :size="20" />
          <BarChart3 v-if="tab.icon === 'bar-chart'" :size="20" />
        </span>
        <span class="label">{{ tab.label }}</span>
        <div class="glow-bar"></div>
      </div>
    </nav>
    
    <!-- <div class="sidebar-footer">
      Created by HenryDaily
    </div> -->
  </aside>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { LogIn, LogOut, Snowflake, SquareActivity, BarChart3 } from 'lucide-vue-next';

defineProps(['currentTab']);
defineEmits(['update:tab']);

const tabs = [
  { id: 'check-in', label: '前台管理', icon: 'log-in' },
  { id: 'user-console', label: '客房控制', icon: 'snowflake' },
  { id: 'monitor', label: '监控系统', icon: 'SquareActivity' },
  { id: 'report', label: '统计报表', icon: 'bar-chart' }
];

const sidebarRef = ref(null);
const isNarrow = ref(false);
let resizeObserver = null;

onMounted(() => {
  if (sidebarRef.value) {
    resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        isNarrow.value = entry.contentRect.width < 120;
      }
    });
    resizeObserver.observe(sidebarRef.value);
  }
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});
</script>

<style scoped lang="scss">
.sidebar-glass {
  height: 100%;
  background: rgba(20, 20, 25, 0.8);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}

/* 窄模式样式 */
.narrow-mode {
  .logo-text { display: none; }
  .label { display: none; }
  .logo-area { 
    justify-content: center; 
    padding: 40px 0; 
    gap: 0;
  }
  .nav-item { 
    justify-content: center; 
    padding: 18px 0; 
    .icon { margin-right: 0; }
  }
}

.logo-area {
  padding: 40px 30px;
  display: flex;
  align-items: center;
  gap: 15px;
  
  .logo-icon {
    width: 40px; height: 40px;
    background: var(--primary);
    color: #000;
    font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    border-radius: 8px;
    box-shadow: 0 0 15px var(--primary);
  }
  .logo-text { font-size: 12px; font-weight: bold; letter-spacing: 2px; line-height: 1.2; }
}

.nav-menu {
  flex: 1;
  padding: 20px 0;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: 18px 30px;
  cursor: pointer;
  transition: all 0.3s;
  color: var(--text-sec);
  
  .icon { margin-right: 15px; font-size: 18px; transform: translateY(2px);}
  .label { font-size: 14px; font-weight: 500; }
  .glow-bar {
    position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--primary);
    box-shadow: 0 0 10px var(--primary);
    opacity: 0;
    transition: 0.3s;
  }

  &:hover {
    background: rgba(255,255,255,0.03);
    color: #fff;
  }

  &.active {
    background: linear-gradient(90deg, var(--primary-dim), transparent);
    color: #fff;
    .glow-bar { opacity: 1; }
    .icon { text-shadow: 0 0 10px var(--primary); }
  }
}

.sidebar-footer {
  padding: 20px;
  font-size: 10px;
  color: rgba(255,255,255,0.2);
  text-align: center;
}
</style>