<template>
  <div class="glass-container full-height">
    
    <!-- ================= 左侧：控制面板 ================= -->
    <div class="panel-section left-control">
      <header class="section-header">

        <div class="accent-icon">
        <component :is="actionIcon" :size="20"/> </div>
        <div class="accent-title"> {{ actionTitle }}</div>
        <span class="date">{{ currentDate }}</span>
      </header>

      <div class="control-body">
        <!-- 房间状态大卡片 -->
        <div class="room-status-display" :class="statusClass">
          <div v-if="selectedRoom" class="room-content">
            <div class="r-number">{{ selectedRoom.id }}</div>
            <div class="r-meta">
              <span class="tag">{{ selectedRoom.type }}</span>
              <span class="tag price">¥{{ selectedRoom.price }}/晚</span>
            </div>
            <div class="r-state">
              <span class="dot" :class="selectedRoom.isFree ? 'free' : 'busy'"></span>
              {{ selectedRoom.isFree ? '空闲' : '已入住' }}
            </div>
          </div>
          <div v-else class="placeholder-text">
            <div class="icon-box"><MousePointerClick :size="32"/></div>
            请在右侧选择房间
          </div>
        </div>

        <!-- 动态操作区 -->
        <div v-if="selectedRoom" class="action-area">
          
          <!-- 情况A: 房间空闲 -> 显示入住表单 -->
          <div v-if="selectedRoom.isFree" class="check-in-form fade-in">
            <div class="input-row center-text">
              <label class="day-count-subtitle">确认入住信息</label>
            </div>
            
            <!-- 押金输入 -->
            <div class="input-group">
              <label>押金 (¥)</label>
              <input type="number" v-model="deposit" class="neon-input-field" />
            </div>

            <!-- 订餐选择 -->
            <div class="food-selection">
              <label>订餐服务</label>
              <div v-for="item in foodMenu" :key="item.id" class="food-item">
                <span>{{ item.name }} (¥{{ item.price }})</span>
                <div class="counter">
                  <button @click="foodOrders[item.id] > 0 && foodOrders[item.id]--">-</button>
                  <span>{{ foodOrders[item.id] }}</span>
                  <button @click="foodOrders[item.id]++">+</button>
                </div>
              </div>
            </div>

            <div class="cost-preview">
              当前房价: <span>¥{{ selectedRoom.price }}/晚</span>
            </div>
            <button class="neon-btn primary big-btn" :disabled="isProcessing" @click="handleCheckIn">
              {{ isProcessing ? '系统处理中...' : '办理入住' }}
            </button>
          </div>

          <!-- 情况B: 房间已满 -> 显示退房按钮 -->
          <div v-else class="check-out-action fade-in">
            <div class="info-msg">
              该房间当前有客人入住<br>点击下方按钮查看详单
            </div>
            <button class="neon-btn danger big-btn" @click="openCheckOutModal">
              退房结算
            </button>
          </div>

        </div>
      </div>
    </div>

    <!-- ================= 右侧：房态概览 ================= -->
    <div class="panel-section right-grid">
      <header class="section-header">
        <h3>房态概览</h3>
      </header>

      <div class="floors-container">
        <div v-for="floor in floors" :key="floor.level" class="floor-row">
          <div class="floor-mark">{{ floor.level }}F</div>
          <div class="room-matrix">
            <button 
              v-for="room in floor.rooms" 
              :key="room.id"
              class="room-cell"
              :class="{ 
                'busy-room': !room.isFree, 
                'free-room': room.isFree,
                'selected': selectedRoom?.id === room.id 
              }"
              @click="handleRoomSelect(room)"
            >
              <span class="id">{{ room.id }}</span>
              <!-- 区分显示图标 -->
              <span class="icon-state">
                <User v-if="!room.isFree" :size="12" />
                <BedDouble v-else :size="12" />
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ================= 弹窗：退房结算详情 ================= -->
    <Transition name="modal">
      <div v-if="showCheckoutModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-content glass-container">
          <header class="modal-header">
            <h2><LogOut :size="20" /> {{ selectedRoom?.id }} 退房结算</h2>
            <button class="close-btn" @click="closeModal"><X :size="24"/></button>
          </header>

          <div v-if="!billData" class="loading-state">
            <Loader2 class="spin" :size="40" />
            <p>正在拉取账单数据...</p>
          </div>

          <div v-else class="bill-layout">
            <!-- 左侧：详单 -->
            <div class="detail-panel">
              <div class="card basic-info">
                <h3>住宿信息</h3>
                <div class="info-row">
                  <span>房型: {{ billData.roomType }}</span>
                  <span>入住: {{ billData.checkInDate }} ({{ billData.days }}天)</span>
                  <span class="cost">¥{{ billData.stayFee.toFixed(2) }}</span>
                </div>
              </div>

              <div class="card ac-list">
                <h3>消费详单 (空调/餐饮)</h3>
                <div class="table-scroll">
                  <table>
                    <thead><tr><th>项目</th><th>详情</th><th>数量/时长</th><th>费用</th></tr></thead>
                    <tbody>
                      <tr v-for="(r, i) in billData.records" :key="i">
                        <td>{{ r.name }}</td>
                        <td><span class="badge">{{ r.detail }}</span></td>
                        <td>{{ r.qty }}</td>
                        <td>¥{{ r.fee }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="subtotal">
                  <div>空调费: ¥{{ billData.extraFee.toFixed(2) }}</div>
                  <div>餐饮费: ¥{{ (billData.foodFee || 0).toFixed(2) }}</div>
                  <div>已付押金: ¥{{ (billData.deposit || 0).toFixed(2) }}</div>
                </div>
              </div>
            </div>

            <!-- 右侧：金额与支付 -->
            <div class="action-panel">
              <div class="total-display">
                <label>总应付金额</label>
                <div class="amount">
                  <small>¥</small>{{ (billData.stayFee + billData.extraFee + (billData.foodFee || 0) - (billData.deposit || 0)).toFixed(2) }}
                </div>
                <div class="breakdown">
                  房费 {{ billData.stayFee.toFixed(2) }} 元<br>
                  空调 {{ billData.extraFee.toFixed(2) }} 元<br>
                  餐饮 {{ (billData.foodFee || 0).toFixed(2) }} 元<br>
                  押金 -{{ (billData.deposit || 0).toFixed(2) }} 元
                </div>
              </div>
              <div class="btn-group">
                <div class="export-row" style="display: flex; gap: 10px;">
                  <button class="neon-btn outline" @click="downloadACBill">导出空调详单</button>
                  <button class="neon-btn outline" @click="downloadStayBill">导出住宿账单</button>
                </div>
                <button class="neon-btn primary big" @click="handlePay">
                  确认收款并退房
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { 
  LogIn, LogOut, User, BedDouble, MousePointerClick, X, Loader2 
} from 'lucide-vue-next';

// --- 基础状态 ---
const currentDate = new Date().toLocaleDateString();
const floors = ref([]);
const selectedRoom = ref(null);
const isProcessing = ref(false);

// --- 入住相关状态 ---
const days = ref(1);
const deposit = ref(0);
const foodMenu = [
  { id: 'coke', name: '可乐', price: 5 },
  { id: 'burger', name: '汉堡', price: 20 },
  { id: 'pasta', name: '意大利面', price: 35 }
];
const foodOrders = ref({}); // { coke: 0, burger: 0, pasta: 0 }

// 初始化 foodOrders
foodMenu.forEach(item => {
  foodOrders.value[item.id] = 0;
});

// --- 退房相关状态 ---
const showCheckoutModal = ref(false);
const billData = ref(null);

// --- 计算属性 ---
const actionIcon = computed(() => selectedRoom.value?.isFree ? LogIn : LogOut);
const actionTitle = computed(() => {
  if (!selectedRoom.value) return '前台操作';
  return selectedRoom.value.isFree ? '办理入住' : '退房结算';
});
const statusClass = computed(() => {
  if (!selectedRoom.value) return '';
  return selectedRoom.value.isFree ? 'status-free' : 'status-busy';
});

// --- 初始化房态数据 (从后端获取) ---
const fetchRooms = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/rooms');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    const data = await response.json();
    floors.value = data;
  } catch (error) {
    console.error('Failed to fetch rooms:', error);
  }
};

// --- 交互逻辑 ---
const handleRoomSelect = (room) => {
  selectedRoom.value = room;
  days.value = 1; // 重置天数
  deposit.value = room.deposit || 0; // 默认押金
  // 重置订餐
  Object.keys(foodOrders.value).forEach(key => {
    foodOrders.value[key] = 0;
  });
};

const handleCheckIn = async () => {
  isProcessing.value = true;
  
  // 构造订餐列表
  const orders = [];
  foodMenu.forEach(item => {
    const count = foodOrders.value[item.id];
    if (count > 0) {
      orders.push({
        name: item.name,
        price: item.price,
        count: count
      });
    }
  });

  // 构造请求数据 (模拟身份证和姓名，实际应从表单获取)
  const payload = {
    room_id: String(selectedRoom.value.id),
    id_card: "110101199001011234", // 示例数据
    name: "张三", // 示例数据
    phone: "13800138000", // 示例数据
    deposit: Number(deposit.value),
    food_orders: orders
    // days: days.value // 不再需要前端传递天数
  };

  try {
    const response = await fetch('http://localhost:5000/api/check_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      alert(`房间 ${selectedRoom.value.id} 入住办理成功！`);
      selectedRoom.value.isFree = false;
      // 刷新房态
      fetchRooms();
    } else {
      const err = await response.json();
      alert(`入住失败: ${err.error || '未知错误'}`);
    }
  } catch (e) {
    alert('网络错误，请检查后端服务');
  } finally {
    isProcessing.value = false;
  }
};

const openCheckOutModal = async () => {
  showCheckoutModal.value = true;
  billData.value = null;
  
  try {
    const response = await fetch(`http://localhost:5000/api/room/${selectedRoom.value.id}/bill`);
    if (response.ok) {
      billData.value = await response.json();
    } else {
      alert('获取账单失败');
      showCheckoutModal.value = false;
    }
  } catch (e) {
    console.error(e);
    alert('网络错误');
    showCheckoutModal.value = false;
  }
};

const closeModal = () => {
  showCheckoutModal.value = false;
};

const downloadACBill = () => {
  if (!selectedRoom.value) return;
  window.open(`http://localhost:5000/api/room/${selectedRoom.value.id}/export/ac_bill`, '_blank');
};

const downloadStayBill = () => {
  if (!selectedRoom.value) return;
  window.open(`http://localhost:5000/api/room/${selectedRoom.value.id}/export/stay_bill`, '_blank');
};

const handlePay = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/check_out', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room_id: String(selectedRoom.value.id) })
    });

    if (response.ok) {
      alert('收款成功，退房完成');
      showCheckoutModal.value = false;
      selectedRoom.value.isFree = true;
      selectedRoom.value = null;
      fetchRooms();
    } else {
      alert('退房失败');
    }
  } catch (e) {
    alert('网络错误');
  }
};

onMounted(fetchRooms);
</script>

<style scoped lang="scss">
@import '../common-panel.css'; /* 假设这是你的公共样式文件 */

/* 布局调整 */
.glass-container {
  display: flex;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

/* 左侧控制面板 */
.left-control {
  width: 350px;
  display: flex; flex-direction: column;
  padding-right: 20px;
}

.control-body {
  flex: 1; display: flex; flex-direction: column; gap: 30px;
  justify-content: flex-start;
  padding-top: 20px;
  min-height: 0;
}

/* 房间状态大展示卡 */
.room-status-display {
  border: 1px dashed rgba(255,255,255,0.2);
  border-radius: 16px;
  padding: 30px 20px;
  text-align: center;
  transition: all 0.3s;
  background: rgba(0,0,0,0.2);

  .placeholder-text {
    color: var(--text-sec);
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    .icon-box { opacity: 0.5; }
  }

  /* 统一选中状态样式 */
  &.status-free {
    border: 1px solid var(--primary);
    background: linear-gradient(180deg, #00F2FF1A, transparent);
    .r-number { color: var(--primary); }
  }
  &.status-busy {
    border: 1px solid #ff9d00;
    background: linear-gradient(180deg, rgba(255, 157, 0, 0.1), transparent);
    .r-number { color: #ff9d00; }
  }

  .room-content {
    .r-number { font-size: 48px; font-weight: 800; line-height: 1; margin-bottom: 10px; font-family: 'Courier New', monospace; letter-spacing: -2px;}
    .r-meta { display: flex; gap: 10px; justify-content: center; margin-bottom: 15px; }
    .tag { background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    .tag.price { color: #ffd700; background: rgba(255, 215, 0, 0.1); }
    .r-state { font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 6px; }
  }
}

/* 动态操作区 */
.action-area {
  flex: 1;
  display: flex; flex-direction: column; justify-content: flex-end;
  padding-bottom: 20px;
}

.fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* 入住表单 */
.check-in-form {
  .input-row { margin-bottom: 20px; }
  .number-input {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    input { width: 60px; text-align: center; font-size: 18px; font-weight: bold; }
    button { 
      width: 40px; height: 40px; border-radius: 8px; border: 1px solid var(--border); 
      background: rgba(255,255,255,0.05); color: #fff; cursor: pointer;
      &:hover { background: var(--primary); color: #000; border-color: var(--primary); }
    }
  }
  .cost-preview {
    text-align: center; margin-bottom: 20px; color: var(--text-sec); font-size: 14px;
    span { color: #ffd700; font-size: 18px; font-weight: bold; margin-left: 5px; }
  }
}

/* 退房提示 */
.check-out-action {
  text-align: center;
  .info-msg { margin-bottom: 20px; color: var(--text-sec); line-height: 1.5; font-size: 13px; }
  .neon-btn.danger {
    background: linear-gradient(135deg, #ff9d00, #cc7a00);
    color: #fff;
    &:hover { box-shadow: 0 0 15px rgba(255, 157, 0, 0.5); }
  }
}

/* 右侧房态矩阵 */
.right-grid { 
  flex: 1; 
  display: flex; 
  flex-direction: column;
  min-height: 0;
}

.floors-container { 
  flex: 1; 
  overflow-y: auto; 
  padding: 10px;
  /* 隐藏右侧房态概览区域的滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE 10+ */
  &::-webkit-scrollbar {
    width: 0px;
    background: transparent; /* Chrome/Safari/Webkit */
  }
}

.floor-row { display: flex; align-items: center; margin-bottom: 20px; }
.floor-mark { font-size: 24px; font-weight: bold; color: rgba(255,255,255,0.1); width: 50px; }
.room-matrix { flex: 1; display: flex; flex-wrap: wrap; gap: 12px; }

/* 房间方块样式重构 */
.room-cell {
  width: 75px; height: 60px; border-radius: 8px; 
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.2s; position: relative;
  padding: 5px;
  
  .id { font-weight: bold; font-size: 15px; }
  .icon-state { margin-top: 4px; opacity: 0.6; }

  /* 空闲状态 */
  &.free-room {
    background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: #fff;
    &:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
  }
  
  /* 入住状态 */
  &.busy-room {
    background: rgba(40, 40, 40, 0.8); border: 1px solid rgba(255,255,255,0.1); color: #888;
    &:hover { border-color: #ff9d00; color: #fff; transform: translateY(-2px); }
    .icon-state { color: #ff9d00; opacity: 0.8; }
  }

  /* 选中状态 (覆盖上述两种) */
  &.selected {
    z-index: 2;
    transform: scale(1.1);
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
    
    &.free-room {
      background: var(--primary); color: #000; border-color: var(--primary);
      .icon-state { color: #000; }
    }
    &.busy-room {
      background: #ff9d00; color: #fff; border-color: #ff9d00;
      .icon-state { color: #fff; }
    }
  }
}

/* 图例颜色 */
.dot.selected-legend { background: var(--primary); border: 1px solid #fff; }

/* 大按钮样式 */
.big-btn {
  width: 100%;
  padding: 15px 20px;
  font-size: 18px;
  font-weight: bold;
  margin-top: 10px;
}

/* ================= 模态窗样式 ================= */
.modal-overlay {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(5px);
  z-index: 100;
  display: flex; align-items: center; justify-content: center;
}

.modal-content {
  width: 90%; max-width: 900px; height: 80%;
  background: #1a1a1a; /* 此时需要深色背景防止透明透到底部内容 */
  box-shadow: 0 25px 50px rgba(0,0,0,0.8);
  display: flex; flex-direction: column;
  border: 1px solid var(--border);
}

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 20px; border-bottom: 1px solid var(--border);
  h2 { font-size: 20px; display: flex; align-items: center; gap: 10px; color: #fff; }
  .close-btn { background: none; border: none; color: #fff; cursor: pointer; opacity: 0.6; &:hover{ opacity: 1; } }
}

.loading-state {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--primary);
  .spin { animation: spin 1s linear infinite; margin-bottom: 15px; }
}
@keyframes spin { 100% { transform: rotate(360deg); } }

/* 复用原CheckOut内部样式 */
.bill-layout { flex: 1; display: flex; gap: 20px; overflow: hidden; margin-top: 20px; }
.detail-panel { flex: 2; display: flex; flex-direction: column; gap: 15px; overflow-y: auto; }
.card { background: rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); }
.card h3 { font-size: 14px; color: var(--primary); margin-bottom: 10px; border-left: 3px solid var(--primary); padding-left: 10px; }
.table-scroll { max-height: 250px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td, th { text-align: left; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #ddd; }
th { color: var(--text-sec); font-weight: normal; }
.badge { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 10px; border: 1px solid #444; }

.action-panel {
  flex: 1; background: rgba(0,0,0,0.3); padding: 20px; border-radius: 8px;
  display: flex; flex-direction: column; justify-content: space-between;
}
.total-display {
  text-align: right;
  .amount { font-size: 42px; color: #fff; margin: 10px 0; font-weight: 300; small { font-size: 24px; } }
  .breakdown { font-size: 12px; color: var(--text-sec); }
}
.btn-group { display: flex; flex-direction: column; gap: 10px; }

/* 模态窗过渡动画 */
.modal-enter-active, .modal-leave-active { transition: opacity 0.3s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

.day-count-btn{
  font-size: 24px;
  text-align: center;
}
.neon-input {
  text-align: center;
}
.day-count-subtitle{
  font-size: 18px;
  color: #fff;
  text-align: center;
  padding: 10px 0;
}
.input-group {
  margin-bottom: 15px;
  label { display: block; color: var(--text-sec); margin-bottom: 5px; font-size: 14px; }
  .neon-input-field {
    width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    color: #fff; padding: 8px; border-radius: 4px; text-align: center;
    &:focus { border-color: var(--primary); outline: none; }
  }
}
.food-selection {
  margin-bottom: 20px;
  label { display: block; color: var(--text-sec); margin-bottom: 10px; font-size: 14px; }
  .food-item {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px; font-size: 14px;
    .counter {
      display: flex; align-items: center; gap: 8px;
      button {
        width: 24px; height: 24px; border-radius: 4px; border: 1px solid var(--border);
        background: rgba(255,255,255,0.1); color: #fff; cursor: pointer;
        &:hover { background: var(--primary); color: #000; }
      }
      span { width: 20px; text-align: center; }
    }
  }
}
.number-display{
  font-size: 20px;
  text-align: center;
  width: 100px;
}
.accent-title{
position:relative;
right: 70px;
}
.accent-icon{
transform: translateY(2px);
}
</style>