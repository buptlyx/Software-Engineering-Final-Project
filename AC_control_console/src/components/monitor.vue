<template>
  <div class="monitor-layout-wrapper">
    <div class="glass-container monitor-panel">
      <!-- 1. 顶部全局数据板 -->
      <header class="dashboard-header">
        <div class="header-title">
          <Activity class="icon-lg text-primary" />
          <h2>中央监控台</h2>
        </div>
        
        <div class="kpi-group">
          <div class="kpi-card">
            <div class="label">在线终端</div>
            <div class="value text-primary">{{ activeCount }} <span class="unit">/ 40</span></div>
          </div>
          <div class="kpi-card warning">
            <div class="label">排队等待</div>
            <div class="value text-warning">{{ waitingCount }}</div>
          </div>
          <div class="kpi-card">
            <div class="label">实时营收</div>
            <div class="value">¥ {{ totalRevenue.toFixed(2) }}</div>
          </div>
        </div>
      </header>

      <!-- 2. 过滤器与楼层指示 -->
      <div class="toolbar">
        <div class="filter-tabs">
          <button 
            v-for="f in ['全部', '服务中', '等待中']" 
            :key="f"
            class="tab-btn"
            :class="{ active: filterType === f }"
            @click="filterType = f"
          >
            {{ f }}
          </button>
        </div>
        <div class="legend">
          <span class="dot serving"></span> 服务中
          <span class="dot waiting"></span> 等待中
          <span class="dot idle"></span> 关机
        </div>
      </div>

      <!-- 3. 房间监控矩阵 -->
      <div class="room-grid-scroll">
        <div class="room-grid">
          <transition-group name="list">
            <div 
              v-for="room in filteredRooms" 
              :key="room.id"
              class="room-card"
              :class="room.status"
            >
              <!-- 房间号与状态标 -->
              <div class="card-header">
                <span class="room-id">{{ room.id }}</span>
                <span class="status-dot"></span>
              </div>

              <!-- 运行数据 (仅开机显示) -->
              <div v-if="room.status !== 'idle'" class="card-body">
                <div class="data-row">
                  <span class="temp-current">{{ room.currentTemp.toFixed(1) }}°</span>
                  <span class="temp-target"><Crosshair class="icon-xxs"/> {{ room.targetTemp }}°</span>
                </div>
                
                <div class="data-row detail">
                  <span class="fan-tag" :class="room.fanSpeed">
                    <Fan class="icon-xxs" :class="{ spin: room.status === 'serving' }"/> 
                    {{ room.fanSpeed }}
                  </span>
                  <span class="fee">¥{{ room.fee.toFixed(1) }}</span>
                </div>

                <!-- 调度状态条 -->
                <div class="status-bar">
                  <span v-if="room.status === 'serving'" class="text-primary">Serving</span>
                  <span v-else class="text-warning">Queueing...</span>
                </div>
              </div>

              <!-- 关机占位 -->
              <div v-else class="card-body idle-body">
                <Power class="icon-md text-dim"/>
                <span>OFFLINE</span>
              </div>
            </div>
          </transition-group>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Activity, Fan, Power, Crosshair } from 'lucide-vue-next';

// --- API Configuration ---
const API_BASE_URL = 'http://127.0.0.1:5000/api/room';

// --- State ---
const rooms = ref([]);
const filterType = ref('全部');
let monitorTimer = null;

// 生成 40 个房间号 (101-110, ... 401-410)
const roomIds = [];
for (let f = 1; f <= 4; f++) {
  for (let r = 1; r <= 10; r++) {
    roomIds.push(`${f}${r.toString().padStart(2, '0')}`);
  }
}

// --- Fetch Data from Backend ---
const fetchAllRooms = async () => {
  try {
    const promises = roomIds.map(roomId =>
      fetch(`${API_BASE_URL}/${roomId}/status`)
        .then(res => res.ok ? res.json() : null)
        .catch(() => null)
    );
    
    const results = await Promise.all(promises);
    
    rooms.value = results.map((data, index) => {
      if (!data) return null;
      
      const roomId = roomIds[index];
      // 根据后端数据判断房间状态
      let status = 'idle';
      if (data.power_on) {
        status = data.is_active ? 'serving' : 'idle';
      }
      
      return {
        id: roomId,
        status: status,
        currentTemp: data.current_temp,
        targetTemp: data.target_temp,
        fanSpeed: data.fan_speed,
        fee: data.total_fee,
        isActive: data.is_active,
        powerOn: data.power_on
      };
    }).filter(r => r !== null);
  } catch (e) {
    console.error("Failed to fetch rooms:", e);
  }
};

// --- Computed Stats ---
const activeCount = computed(() => rooms.value.filter(r => r.powerOn && r.status !== 'idle').length);
const waitingCount = computed(() => rooms.value.filter(r => r.status === 'waiting').length);
const totalRevenue = computed(() => rooms.value.reduce((sum, r) => sum + r.fee, 0));

const filteredRooms = computed(() => {
  if (filterType.value === '全部') return rooms.value;
  if (filterType.value === '服务中') return rooms.value.filter(r => r.status === 'serving');
  if (filterType.value === '等待中') return rooms.value.filter(r => r.status === 'waiting' || (!r.powerOn && r.status !== 'idle'));
  return rooms.value;
});

// --- Start Monitor ---
const startMonitor = () => {
  if (monitorTimer) clearInterval(monitorTimer);
  // 每秒更新一次房间数据
  fetchAllRooms();
  monitorTimer = setInterval(fetchAllRooms, 1000);
};

onMounted(() => {
  startMonitor();
});

onUnmounted(() => {
  if (monitorTimer) clearInterval(monitorTimer);
});
</script>

<style scoped lang="scss">
/* --- 变量 (保持统一) --- */
$primary: var(--primary); /* Cyan */
$warning: #ff9d00;        /* Orange */
$bg-panel: rgba(30, 35, 48, 0.6);
$border: var(--border);
$text-sec: rgba(255, 255, 255, 0.5);

/* Layout Wrappers */
.monitor-layout-wrapper {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  padding: 30px;
}

.monitor-panel {
  width: 100%; height: 100%;
  background: $bg-panel;
  backdrop-filter: blur(20px);
  border: 1px solid $border;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* 1. Header */
.dashboard-header {
  height: 80px; padding: 0 30px;
  background: rgba(0,0,0,0.2); border-bottom: 1px solid $border;
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;

  .header-title {
    display: flex; align-items: center; gap: 10px;
    h2 { font-size: 18px; color: #fff; letter-spacing: 1px; }
    .icon-lg { width: 24px; height: 24px; }
  }

  .kpi-group {
    display: flex; gap: 30px;
    .kpi-card {
      text-align: right;
      .label { font-size: 12px; color: $text-sec; text-transform: uppercase; }
      .value { font-size: 24px; font-weight: bold; color: #fff; font-family: monospace; }
      .unit { font-size: 14px; color: $text-sec; }
      
      &.warning .value { color: $warning; text-shadow: 0 0 10px rgba(255, 157, 0, 0.3); }
    }
  }
}

/* 2. Toolbar */
.toolbar {
  height: 50px; padding: 0 30px;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  flex-shrink: 0;

  .filter-tabs {
    display: flex; gap: 5px;
    .tab-btn {
      background: transparent; border: 1px solid transparent; color: $text-sec;
      padding: 5px 15px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: 0.2s;
      &.active { background: rgba(255,255,255,0.1); color: #fff; border-color: $border; }
      &:hover { color: #fff; }
    }
  }

  .legend {
    display: flex; gap: 15px; font-size: 12px; color: $text-sec; align-items: center;
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .serving { background: $primary; box-shadow: 0 0 5px $primary; }
    .waiting { background: $warning; box-shadow: 0 0 5px $warning; }
    .idle { background: rgba(255,255,255,0.2); }
  }
}

/* 3. Grid */
.room-grid-scroll {
  flex: 1; overflow-y: auto; padding: 20px 30px;
  
  /* 自定义滚动条 */
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
}

.room-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
}

/* Room Card Design */
.room-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 15px;
  display: flex; flex-direction: column; gap: 10px;
  transition: all 0.3s;
  position: relative; overflow: hidden;

  /* idle State */
  &.idle {
    opacity: 0.6;
    .idle-body { 
      height: 60px; display: flex; flex-direction: column; align-items: center; justify-content: center; 
      color: $text-sec; font-size: 12px; gap: 5px;
    }
  }

  /* Serving State */
  &.serving {
    border-color: rgba(0, 242, 255, 0.3);
    background: linear-gradient(160deg, rgba(0, 242, 255, 0.05), transparent);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    .status-dot { background: $primary; box-shadow: 0 0 8px $primary; }
    .room-id { color: #fff; }
  }

  /* Waiting State */
  &.waiting {
    border-color: rgba(255, 157, 0, 0.3);
    background: linear-gradient(160deg, rgba(255, 157, 0, 0.05), transparent);
    .status-dot { background: $warning; box-shadow: 0 0 8px $warning; animation: blink 1s infinite; }
    .room-id { color: $warning; }
  }

  .card-header {
    display: flex; justify-content: space-between; align-items: center;
    .room-id { font-size: 16px; font-weight: bold; font-family: monospace; color: $text-sec; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.2); }
  }

  .card-body {
    display: flex; flex-direction: column; gap: 8px;
    
    .data-row {
      display: flex; justify-content: space-between; align-items: baseline;
      &.detail { align-items: center; margin-top: 5px; }
    }

    .temp-current { font-size: 24px; font-weight: 300; color: #fff; line-height: 1; }
    .temp-target { font-size: 12px; color: $text-sec; display: flex; align-items: center; gap: 2px; }

    .fan-tag {
      font-size: 10px; padding: 2px 6px; border-radius: 4px; 
      background: rgba(255,255,255,0.1); color: $text-sec; display: flex; align-items: center; gap: 4px;
      
      &.High { color: #ff5555; background: rgba(255, 85, 85, 0.1); }
      &.Mid { color: $primary; background: rgba(0, 242, 255, 0.1); }
      &.Low { color: #fff; }
    }
    
    .fee { font-size: 12px; font-family: monospace; color: #fff; }
    
    .status-bar {
      font-size: 10px; text-transform: uppercase; font-weight: bold; text-align: right; margin-top: 5px;
    }
  }
}

/* Helpers */
.text-primary { color: $primary; }
.text-warning { color: $warning; }
.text-dim { color: rgba(255,255,255,0.2); }
.icon-xxs { width: 10px; height: 10px; }
.icon-md { width: 20px; height: 20px; }
.spin { animation: spin 2s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Transition for list */
.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: scale(0.9); }
</style>