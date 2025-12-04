<template>
  <div class="glass-container full-height">
    <!-- 左侧：表单区 -->
    <div class="panel-section left-form">
      <header class="section-header">
        <h2><span class="accent-icon"><LogIn :size="18" /></span> 顾客登记</h2>
        <span class="date">{{ currentDate }}</span>
      </header>
      
      <div class="form-body">
        <div class="input-row">
          <label>身份证号</label>
          <input v-model="form.idCard" class="neon-input" placeholder="输入证件号..." />
        </div>
        <div class="input-row">
          <label>顾客姓名</label>
          <input v-model="form.name" class="neon-input" placeholder="姓名" />
        </div>
        <div class="input-grid-2">
          <div class="input-row">
            <label>电话</label>
            <input v-model="form.phone" class="neon-input" />
          </div>
          <div class="input-row">
            <label>天数</label>
            <input v-model="form.days" type="number" min="1" class="neon-input" @input="validateDays" />
          </div>
        </div>
        
        <!-- 选房状态卡片 -->
        <div class="room-status-card" :class="{ active: selectedRoom }">
          <div v-if="selectedRoom">
            <div class="r-id">{{ selectedRoom.id }}</div>
            <div class="r-info">{{ selectedRoom.type }} | ¥{{ selectedRoom.roomPrice }}/晚</div>
          </div>
          <div v-else class="placeholder">请在右侧选择房间</div>
        </div>
      </div>

      <footer class="form-footer">
        <button class="neon-btn primary" :disabled="!isValid" @click="handleCheckIn">
          {{ isProcessing ? '制卡中...' : '确认入住' }}
        </button>
      </footer>
    </div>

    <!-- 右侧：房态图 -->
    <div class="panel-section right-grid">
      <header class="section-header">
        <h3>房态概览</h3>
        <div class="legend">
          <span class="dot free"></span>空闲
          <span class="dot busy"></span>占用
        </div>
      </header>

      <div class="floors-container">
        <div v-for="floor in floors" :key="floor.level" class="floor-row">
          <div class="floor-mark">{{ floor.level }}F</div>
          <div class="room-matrix">
            <button 
              v-for="room in floor.rooms" 
              :key="room.id"
              class="room-cell"
              :class="{ busy: !room.isFree, selected: selectedRoom?.id === room.id }"
              :disabled="!room.isFree"
              @click="selectedRoom = room"
            >
              <span class="id">{{ room.id }}</span>
              <span class="type">{{ room.type === '大床' ? 'K' : 'S' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { reactive } from 'vue';

// --- 全局单例状态 ---
// 使用 reactive 定义全局状态，确保跨组件切换时数据不丢失
// 且保持响应式，避免输入框锁死问题
const globalState = reactive({
  form: { idCard: '', name: '', phone: '', days: 1 },
  selectedRoomId: null
});
</script>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { LogIn } from 'lucide-vue-next';

const API_BASE = 'http://127.0.0.1:5000';
const currentDate = new Date().toLocaleDateString();
const isProcessing = ref(false);

// 直接使用全局响应式对象，无需本地拷贝和同步
const form = globalState.form;
const selectedRoom = ref(null);
const floors = ref([]);

const isValid = computed(() => form.idCard && form.name && selectedRoom.value && form.days > 0);

const validateDays = () => {
  if (form.days !== '' && form.days <= 0) {
    form.days = 1;
  }
};

// 监听选中房间变化，更新全局ID
watch(selectedRoom, (newVal) => {
  globalState.selectedRoomId = newVal ? newVal.id : null;
});

// 从后端获取房间状态
const fetchRoomStatus = async (roomId) => {
  try {
    const response = await fetch(`${API_BASE}/api/room/${roomId}/status`);
    if (response.ok) {
      const data = await response.json();
      return data;
    }
  } catch (error) {
    console.error(`获取房间 ${roomId} 状态失败:`, error);
  }
  return null;
};

const initRooms = async () => {
  const f = [];
  for (let i = 1; i <= 4; i++) {
    const rooms = [];
    for (let j = 1; j <= 10; j++) {
      const roomId = `${i}${j.toString().padStart(2, '0')}`;
      const status = await fetchRoomStatus(roomId);
      
      rooms.push({
        id: roomId,
        type: j > 8 ? '大床' : '标间',
        roomPrice: status ? status.room_price : 0,
        isFree: status ? !status.tenant_id : true // 如果有 tenant_id 则不空闲
      });
    }
    f.push({ level: i, rooms });
  }
  floors.value = f;
  
  // 恢复选中状态
  if (globalState.selectedRoomId) {
    for (const floor of f) {
      const found = floor.rooms.find(r => r.id === globalState.selectedRoomId);
      if (found && found.isFree) {
        selectedRoom.value = found;
        break;
      } else if (found && !found.isFree) {
        // 如果房间被占用了，清除全局选中状态
        globalState.selectedRoomId = null;
      }
    }
  }
};

const handleCheckIn = async () => {
  isProcessing.value = true;
  try {
    const response = await fetch(`${API_BASE}/api/check_in`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        room_id: selectedRoom.value.id,
        id_card: form.idCard,
        name: form.name,
        phone: form.phone,
        days: form.days
      })
    });

    const data = await response.json();
    if (response.ok) {
      alert(`入住成功！\n房间: ${selectedRoom.value.id}\n费用: ¥${selectedRoom.value.roomPrice}/晚\n天数: ${form.days}天`);
      
      // 重置表单 (直接修改全局响应式对象)
      form.idCard = '';
      form.name = '';
      form.phone = '';
      form.days = 1;
      
      selectedRoom.value = null;
      globalState.selectedRoomId = null;
      
      // 刷新房间状态
      await initRooms();
    } else {
      alert(`入住失败: ${data.error}`);
    }
  } catch (error) {
    console.error("Check-in error:", error);
    alert("入住请求失败，请检查网络连接");
  } finally {
    isProcessing.value = false;
  }
};

onMounted(() => {
  initRooms();
});
</script>

<style scoped lang="scss">
/* 引入通用面板样式 */
@import '../common-panel.css';

/* 强制允许输入框交互，防止全局 user-select: none 影响 */
input {
  user-select: auto !important;
  -webkit-user-select: auto !important;
}

.glass-container {
  display: grid;
  grid-template-columns: 320px 1fr; /* 左侧固定，右侧弹性 */
  gap: 20px;
  width: 100%;
  height: 100%;
}

.left-form {
  display: flex; flex-direction: column;
}
.form-body { flex: 1; padding: 20px 0; }
.room-status-card {
  margin-top: 20px; padding: 20px; border: 1px dashed var(--border); border-radius: 12px;
  text-align: center; color: var(--text-sec);
  &.active { border: 1px solid var(--primary); background: var(--primary-dim); color: #fff; }
  .r-id { font-size: 32px; font-weight: bold; color: var(--primary); }
}

.right-grid {
  display: flex; flex-direction: column;
}
.floors-container {
  flex: 1; overflow-y: auto; padding-right: 10px;padding-top: 15px;
}
.floor-row {
  display: flex; align-items: center; margin-bottom: 15px;
  .floor-mark { font-size: 24px; font-weight: bold; color: rgba(255,255,255,0.1); width: 50px; }
  .room-matrix { flex: 1; display: flex; flex-wrap: wrap; gap: 10px; }
}
.room-cell {
  width: 70px; height: 50px; border-radius: 8px; border: 1px solid var(--border);
  background: rgba(255,255,255,0.05); color: #fff; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  transition: all 0.2s;
  
  &:hover:not(:disabled) { border-color: var(--primary); transform: translateY(-2px); }
  &.selected { background: var(--primary); color: #000; box-shadow: 0 0 15px var(--primary); }
  &.busy { background: #515b5d36; color: #5555558a; border-color: transparent; cursor: not-allowed; }
  
  .id { font-size: 14px; font-weight: bold; }
  .type { font-size: 10px; opacity: 0.6; }
}

.form-footer {
  padding-top: 20px;
  border-top: 1px solid var(--border);
  
  .neon-btn {
    width: 100%; /* 横跨父容器 */
    font-size: 16px;
    padding: 15px;
  }
}
</style>