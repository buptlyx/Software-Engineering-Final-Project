<template>
  <div class="console-layout-wrapper">
    <div class="glass-container console-panel">
      <!-- 顶部状态栏 -->
      <header class="panel-header">
        <div class="header-left">
          <div class="room-badge">
            <MapPin class="icon-sm" />
            <select v-model="currentRoomId" class="room-select">
              <option v-for="id in roomList" :key="id" :value="id">ROOM {{ id }}</option>
            </select>
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
                    <div class="desc">当前费率: {{ getFeeRate }}元/分钟</div>
                  </div>
                </div>
                <div v-else-if="acState.serviceState === 'idle'" class="status-content idle">
                  <div class="icon-box idle">
                    <CheckCircle class="icon-md" />
                  </div>
                  <div class="text-box">
                    <div class="title">待机中</div>
                    <div class="desc">已达到目标温度，停止计费</div>
                  </div>
                </div>
                <div v-else class="status-content waiting">
                  <div class="icon-box waiting">
                    <Hourglass class="icon-md breathing" />
                  </div>
                  <div class="text-box">
                    <div class="title">排队等待</div>
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
import { reactive, computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { 
  Wifi, MapPin, Wind, Hourglass, CheckCircle,
  Coins, Clock, Power, Plus, Minus, Crosshair 
} from 'lucide-vue-next';

const circumference = 2 * Math.PI * 85; 
const API_BASE_URL = 'http://127.0.0.1:5000/api/room';

// --- State & Timers ---
const currentTime = ref('');
const currentRoomId = ref('101');
const roomList = [];
// 生成 40 个房间号 (101-110, ... 401-410)
for (let f = 1; f <= 4; f++) {
  for (let r = 1; r <= 10; r++) {
    roomList.push(`${f}${r.toString().padStart(2, '0')}`);
  }
}

let simulationTimer = null;
let clockTimer = null;
// 房间数据接口（可以随意修改）
const acState = reactive({
  powerOn: false,
  currentTemp: 30,
  targetTemp: 25,
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

const getFeeRate = computed(() => ({ 'Low': '0.33', 'Mid': '0.50', 'High': '1.00' }[acState.fanSpeed]));

// --- API Methods ---
const syncStateToBackend = async () => {
  try {
    await fetch(`${API_BASE_URL}/${currentRoomId.value}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        power_on: acState.powerOn,
        target_temp: acState.targetTemp,
        fan_speed: acState.fanSpeed
      })
    });
  } catch (e) {
    console.error("Failed to sync state:", e);
  }
};

const fetchStatusFromBackend = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/${currentRoomId.value}/status`);
    if (res.ok) {
      const data = await res.json();
      // 同步后端数据
      acState.totalFee = data.total_fee;
      acState.currentTemp = data.current_temp;
      acState.duration = data.duration;
      
      // 更新服务状态
      if (data.is_active) {
        acState.serviceState = 'serving';
      } else {
        acState.serviceState = 'idle';
      }

      // 如果后端也维护开关状态，可以在这里同步，防止多端不一致
      // acState.powerOn = data.power_on; 
      
      // 注意：为了演示效果，如果切换房间，应该同步该房间的开关状态
      // 如果你想让控制台完全反映后端状态，取消下面这行的注释：
      acState.powerOn = data.power_on;
      acState.targetTemp = data.target_temp;
      acState.fanSpeed = data.fan_speed;
    }
  } catch (e) {
    console.error("Failed to fetch status:", e);
  }
};

// 监听房间切换
watch(currentRoomId, () => {
  fetchStatusFromBackend();
});

// --- Methods ---
const handlePower = () => {
  acState.powerOn = !acState.powerOn;
  syncStateToBackend(); // 发送请求
  acState.powerOn ? startPolling() : stopPolling();
};

const changeTemp = (d) => {
  acState.targetTemp += d;
  syncStateToBackend(); // 发送请求
};

const changeSpeed = (s) => {
  acState.fanSpeed = s;
  syncStateToBackend(); // 发送请求
};

const formatDuration = (s) => {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
};

// Polling Logic (原 Simulation Logic)
const startPolling = () => {
  if (simulationTimer) clearInterval(simulationTimer);
  // 立即执行一次
  fetchStatusFromBackend();
  // 每秒轮询一次
  simulationTimer = setInterval(fetchStatusFromBackend, 1000);
};

const stopPolling = () => { 
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
  // 页面加载时先获取一次状态，如果后端已经是开机状态，则自动开启轮询
  fetchStatusFromBackend().then(() => {
    // 可选：如果后端记录是开机，前端也同步为开机
    // if (acState.powerOn) startPolling();
  });
});

onUnmounted(() => {
  stopPolling();
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

    .room-select {
      background: transparent;
      border: none;
      color: #fff;
      font-weight: bold;
      font-size: 12px;
      cursor: pointer;
      outline: none;
      font-family: inherit;
      
      option {
        background: #222;
        color: #fff;
      }
    }
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
    &.idle { color: #00ff9d; box-shadow: 0 0 10px rgba(0,255,157,0.2); }
  }

  .text-box {
    .title { font-size: 14px; font-weight: bold; color: #fff; margin-bottom: 2px; }
    .desc { font-size: 12px; color: $text-sec; }
  }

  &.serving { border: 1px solid rgba(0, 242, 255, 0.3); background: rgba(0, 242, 255, 0.05); }
  &.waiting { border: 1px solid rgba(255, 157, 0, 0.3); background: rgba(255, 157, 0, 0.05); }
  &.idle { border: 1px solid rgba(0, 255, 157, 0.3); background: rgba(0, 255, 157, 0.05); }
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