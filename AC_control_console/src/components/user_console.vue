<template>
  <div class="console-layout-wrapper">
    <div class="glass-container console-panel">
      <!-- 顶部状态栏 -->
      <header class="panel-header">
        <div class="header-left">
          <div class="room-badge">
            <MapPin class="icon-sm" />
            <span>ROOM 302</span>
          </div>
          <div class="status-tag" :class="{ active: acState.powerOn }">
            <Wifi class="icon-xs" :class="{ breathing: acState.powerOn }" />
            {{ acState.powerOn ? 'CONNECTED' : 'OFFLINE' }}
          </div>
        </div>
        <div class="time-display">{{ currentTime }}</div>
      </header>

      <div class="panel-body-grid">
        <!-- 左侧：环境仪表盘 -->
        <section class="visual-section">
          <div class="dial-container">
            <div class="temp-dial-wrapper" :class="{ 'off': !acState.powerOn }">
              <svg class="dial-svg" viewBox="0 0 200 200">
                <circle class="dial-bg" cx="100" cy="100" r="85" />
                <circle 
                  class="dial-progress" 
                  cx="100" cy="100" r="85" 
                  :stroke-dasharray="circumference"
                  :stroke-dashoffset="progressOffset"
                />
              </svg>
              
              <div class="dial-content">
                <div class="label">室内温度</div>
                <div class="big-temp">
                  {{ acState.currentTemp.toFixed(1) }}<span class="unit">°C</span>
                </div>
                <div class="target-hint" v-if="acState.powerOn">
                  <Crosshair class="icon-xs" /> 目标温度: {{ acState.targetTemp }}°C
                </div>
              </div>
            </div>
          </div>

          <transition name="fade">
            <div class="status-card-wrapper" v-if="acState.powerOn">
              <div class="service-status-card" :class="acState.serviceState">
                <div v-if="acState.serviceState === 'serving'" class="status-content">
                  <div class="icon-box serving">
                    <Wind class="icon-md breathing" />
                  </div>
                  <div class="text-box">
                    <div class="title">正在送风</div>
                    <div class="desc">当前费率: {{ getFeeRate }}元/度</div>
                  </div>
                </div>
                <div v-else class="status-content waiting">
                  <div class="icon-box waiting">
                    <Hourglass class="icon-md breathing" />
                  </div>
                  <div class="text-box">
                    <div class="title">排队等待 / Waiting</div>
                    <div class="desc">系统负载高，请稍候...</div>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </section>

        <!-- 右侧：控制面板 -->
        <section class="control-section">
          <div class="stats-row">
            <div class="stat-item">
              <span class="label"><Coins class="icon-xs"/> 当前费用</span>
              <span class="value">¥ {{ acState.totalFee.toFixed(2) }}</span>
            </div>
            <div class="stat-item">
              <span class="label"><Clock class="icon-xs"/> 运行时长</span>
              <span class="value">{{ formatDuration(acState.duration) }}</span>
            </div>
          </div>

          <div class="divider"></div>

          <div class="controls-group" :class="{ disabled: !acState.powerOn }">
            <div class="control-row">
              <label class="row-label">温度设定</label>
              <div class="stepper-box">
                <button class="btn-step" @click="changeTemp(-1)" :disabled="acState.targetTemp <= 16"><Minus class="icon-sm"/></button>
                <span class="step-val">{{ acState.targetTemp }}°</span>
                <button class="btn-step" @click="changeTemp(1)" :disabled="acState.targetTemp >= 30"><Plus class="icon-sm"/></button>
              </div>
            </div>

            <div class="control-row">
              <label class="row-label">风速模式 <span class="sub-label">(影响计费)</span></label>
              <div class="segment-control">
                <button 
                  v-for="speed in ['Low', 'Mid', 'High']" 
                  :key="speed"
                  class="segment-btn"
                  :class="{ active: acState.fanSpeed === speed }"
                  @click="changeSpeed(speed)"
                >
                  {{ speed }}
                </button>
              </div>
            </div>
          </div>

          <div class="power-wrapper">
            <button class="btn-power" :class="{ active: acState.powerOn }" @click="handlePower">
              <Power class="icon-md" :class="{ breathing: acState.powerOn }" />
              <span>{{ acState.powerOn ? '关闭空调' : '启动空调' }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, onUnmounted, ref } from 'vue';
import { 
  Wifi, MapPin, Wind, Hourglass, 
  Coins, Clock, Power, Plus, Minus, Crosshair 
} from 'lucide-vue-next';

const circumference = 2 * Math.PI * 85; 

// --- State & Timers ---
const currentTime = ref('');
let simulationTimer = null;
let clockTimer = null;

const acState = reactive({
  powerOn: false,
  currentTemp: 28.5,
  targetTemp: 22,
  fanSpeed: 'Mid',
  totalFee: 0.0,
  duration: 0,
  serviceState: 'serving'
});

// --- Computed ---
const progressOffset = computed(() => {
  if (!acState.powerOn) return circumference;
  const minT = 16, maxT = 35;
  const percent = Math.max(0, Math.min(1, (acState.currentTemp - minT) / (maxT - minT))); 
  return circumference * (1 - percent);
});

const getFeeRate = computed(() => ({ 'Low': '0.5', 'Mid': '1.0', 'High': '1.5' }[acState.fanSpeed]));

// --- Methods ---
const handlePower = () => {
  acState.powerOn = !acState.powerOn;
  acState.powerOn ? startSimulation() : stopSimulation();
};

const changeTemp = (d) => acState.targetTemp += d;
const changeSpeed = (s) => acState.fanSpeed = s;

const formatDuration = (s) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
};

// Simulation Logic
const startSimulation = () => {
  if (simulationTimer) clearInterval(simulationTimer);
  simulationTimer = setInterval(() => {
    acState.totalFee += { 'Low': 0.01, 'Mid': 0.02, 'High': 0.03 }[acState.fanSpeed];
    if (acState.currentTemp > acState.targetTemp) acState.currentTemp -= 0.05;
    else acState.currentTemp += 0.05;
    acState.duration++;
  }, 1000);
};

const stopSimulation = () => { 
  if (simulationTimer) clearInterval(simulationTimer); 
  simulationTimer = null; 
};

const updateTime = () => {
  currentTime.value = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute:'2-digit' });
};

// --- Lifecycle ---
onMounted(() => {
  updateTime();
  clockTimer = setInterval(updateTime, 10000);
});

onUnmounted(() => {
  stopSimulation();
  if (clockTimer) clearInterval(clockTimer);
});
</script>

<style scoped lang="scss">
/* --- Variables --- */
$primary: var(--primary); 
$bg-panel: rgba(30, 35, 48, 0.6);
$border: var(--border);
$text-sec: rgba(255, 255, 255, 0.5);

/* 
  Wrapper: 
  模拟 CheckIn/CheckOut 的外层容器行为
  Flex 居中，确保 Transition 切换时布局不塌陷
*/
.console-layout-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px; /* 外部留白 */
}

/* Panel Container */
.console-panel {
  width: 100%;
  max-width: 900px;
  height: 600px; /* 固定高度，类似 App 窗口 */
  background: $bg-panel;
  backdrop-filter: blur(20px);
  border: 1px solid $border;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.panel-header {
  height: 60px;
  padding: 0 30px;
  border-bottom: 1px solid $border;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0,0,0,0.2);
  flex-shrink: 0;

  .header-left { display: flex; align-items: center; gap: 15px; }
  
  .room-badge {
    display: flex; align-items: center; gap: 6px;
    font-weight: bold; color: #fff;
    background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 6px;
    font-size: 12px;
  }

  .status-tag {
    display: flex; align-items: center; gap: 6px; font-size: 12px; color: $text-sec;
    &.active { color: $primary; }
  }
  
  .time-display { font-family: monospace; font-size: 14px; color: rgba(255,255,255,0.8); }
}

/* Body Grid */
.panel-body-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
}

/* --- Left Section (Visual) --- */
.visual-section {
  background: rgba(0,0,0,0.2);
  border-right: 1px solid $border;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

.dial-container { margin-bottom: 30px; }

.temp-dial-wrapper {
  position: relative; width: 240px; height: 240px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.5s;

  &.off {
    filter: grayscale(1) brightness(0.4);
    .dial-progress { stroke-dashoffset: 600 !important; opacity: 0; }
  }

  .dial-svg {
    width: 100%; height: 100%; transform: rotate(-90deg);
    overflow: visible; 
    
    .dial-bg { fill: none; stroke: rgba(255,255,255,0.05); stroke-width: 8; }
    .dial-progress {
      fill: none; stroke: $primary; stroke-width: 8; stroke-linecap: round;
      transition: stroke-dashoffset 1s ease;
      filter: drop-shadow(0 0 10px $primary);
    }
  }

  .dial-content {
    position: absolute; text-align: center;
    .label { font-size: 12px; color: $text-sec; letter-spacing: 2px; margin-bottom: 5px; }
    .big-temp { font-size: 56px; font-weight: 200; color: #fff; line-height: 1; .unit { font-size: 24px; color: $text-sec; } }
    .target-hint {
      margin-top: 8px; font-size: 12px; color: $primary;
      display: inline-flex; align-items: center; gap: 4px;
      background: rgba(0, 242, 255, 0.1); padding: 2px 8px; border-radius: 10px;
    }
  }
}

.status-card-wrapper { width: 100%; max-width: 300px; }
.service-status-card {
  padding: 15px; border-radius: 12px;
  background: rgba(255,255,255,0.03);
  
  .status-content { display: flex; align-items: center; gap: 15px; }
  
  .icon-box {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.2);
    
    &.serving { color: $primary; box-shadow: 0 0 10px rgba(0,242,255,0.2); }
    &.waiting { color: #ff9d00; box-shadow: 0 0 10px rgba(255,157,0,0.2); }
  }

  .text-box {
    .title { font-size: 14px; font-weight: bold; color: #fff; margin-bottom: 2px; }
    .desc { font-size: 12px; color: $text-sec; }
  }

  &.serving { border: 1px solid rgba(0, 242, 255, 0.3); background: rgba(0, 242, 255, 0.05); }
  &.waiting { border: 1px solid rgba(255, 157, 0, 0.3); background: rgba(255, 157, 0, 0.05); }
}

/* --- Right Section (Controls) --- */
.control-section {
  padding: 30px;
  display: flex; flex-direction: column;
  background: rgba(255,255,255,0.02);
}

.stats-row {
  display: flex; gap: 20px;
  .stat-item {
    flex: 1;
    background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05);
    padding: 15px; border-radius: 10px;
    display: flex; flex-direction: column; gap: 5px;
    
    .label { display: flex; align-items: center; gap: 5px; font-size: 12px; color: $text-sec; }
    .value { font-size: 18px; font-weight: bold; color: #fff; font-family: monospace; }
  }
}

.divider { height: 1px; background: rgba(255,255,255,0.08); margin: 30px 0; }

.controls-group {
  flex: 1; display: flex; flex-direction: column; gap: 25px;
  transition: opacity 0.3s;
  &.disabled { opacity: 0.4; pointer-events: none; }
}

.control-row {
  .row-label { display: block; font-size: 12px; color: $text-sec; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .sub-label { font-size: 10px; opacity: 0.6; text-transform: none; }
}

.stepper-box {
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(0,0,0,0.2); border-radius: 8px; padding: 4px;
  border: 1px solid rgba(255,255,255,0.1);
  
  .btn-step {
    width: 44px; height: 44px; border: none; background: rgba(255,255,255,0.05);
    color: #fff; border-radius: 6px; cursor: pointer; transition: 0.2s;
    display: flex; align-items: center; justify-content: center;
    &:hover { background: rgba(255,255,255,0.15); }
  }
  .step-val { font-size: 20px; font-weight: bold; }
}

.segment-control {
  display: flex; gap: 5px; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  
  .segment-btn {
    flex: 1; padding: 12px; background: transparent; border: none; color: $text-sec;
    border-radius: 6px; cursor: pointer; font-size: 13px; transition: 0.2s;
    
    &:hover { color: #fff; background: rgba(255,255,255,0.05); }
    &.active { 
      background: $primary; color: #000; font-weight: bold; 
      box-shadow: 0 2px 10px rgba(0,242,255,0.2);
    }
  }
}

.power-wrapper { margin-top: auto; }
.btn-power {
  width: 100%; padding: 18px; border-radius: 10px; border: none;
  font-size: 14px; font-weight: bold; letter-spacing: 1px;
  display: flex; align-items: center; justify-content: center; gap: 10px;
  cursor: pointer; transition: all 0.3s;
  
  background: rgba(85, 142, 255, 0.1); color: #6b99f5; border: 1px solid rgba(38, 130, 204, 0.2);
  
  &.active {
    background: linear-gradient(90deg, #00f2ff, #008cff);
    color: #000; border: 1px solid transparent;
    box-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
  }
  
  &:hover { opacity: 0.9; }
}

/* Animations */
.breathing { animation: breathe 3s ease-in-out infinite; }
@keyframes breathe {
  0%, 100% { opacity: 1; filter: drop-shadow(0 0 5px currentColor); }
  50% { opacity: 0.6; filter: drop-shadow(0 0 1px currentColor); }
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.icon-xs { width: 14px; height: 14px; }
.icon-sm { width: 18px; height: 18px; }
.icon-md { width: 22px; height: 22px; }
</style>