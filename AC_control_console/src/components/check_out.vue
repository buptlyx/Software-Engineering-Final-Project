<template>
  <div class="glass-container full-height">
    <!-- 头部搜索条 -->
    <header class="panel-header-bar">
      <h2><LogOut :size="18" /> 退房结算</h2>
      <div class="search-wrap">
        <input v-model="searchId" @keyup.enter="handleSearch" placeholder="扫描房卡或输入房号..." />
        <button @click="handleSearch">查询</button>
      </div>
    </header>

    <div v-if="!billData" class="empty-placeholder">
      <div class="icon"><Search :size="24" /></div>
      <p>等待查询房间信息...</p>
    </div>

    <!-- 账单内容区：两栏布局 -->
    <div v-else class="bill-layout">
      <!-- 左侧：详单列表 -->
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
          <h3>空调使用详单</h3>
          <div class="table-scroll">
            <table>
              <thead>
                <tr><th>时间</th><th>风速</th><th>时长</th><th>费用</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in billData.acRecords" :key="i">
                  <td>{{ r.startTime }}</td>
                  <td><span class="badge" :class="r.fanSpeed">{{ r.fanSpeed }}</span></td>
                  <td>{{ r.duration }}min</td>
                  <td>¥{{ r.fee }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="subtotal">空调小计: ¥{{ billData.acTotalFee.toFixed(2) }}</div>
        </div>
      </div>

      <!-- 右侧：结算操作 -->
      <div class="action-panel">
        <div class="total-display">
          <label>总应付金额</label>
          <div class="amount">
            <small>¥</small>{{ (billData.stayFee + billData.acTotalFee).toFixed(2) }}
          </div>
          <div class="breakdown">住宿 {{ billData.stayFee }} + 空调 {{ billData.acTotalFee }}</div>
        </div>
        
        <div class="btn-group">
          <button class="neon-btn outline">打印明细</button>
          <button class="neon-btn primary big" @click="handlePay">确认收款并退房</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 逻辑保持模拟 */
import { ref } from 'vue';
import { LogOut, Search } from 'lucide-vue-next';
const searchId = ref('');
const billData = ref(null);
const handleSearch = () => {
  setTimeout(() => {
    billData.value = { 
      roomType: '豪华大床', checkInDate: '2025-11-28', days: 2, stayFee: 600, acTotalFee: 45.5,
      acRecords: [{ startTime: '14:00', fanSpeed: 'High', duration: 120, fee: 30 }, { startTime: '20:00', fanSpeed: 'Low', duration: 60, fee: 15.5 }] 
    };
  }, 300);
};
const handlePay = () => { alert('结账成功'); billData.value = null; searchId.value=''; };
</script>

<style scoped lang="scss">
@import '../common-panel.css';

.glass-container { display: flex; flex-direction: column; }
.panel-header-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 20px; border-bottom: 1px solid var(--border);
  
  .search-wrap {
    display: flex; gap: 10px;
    input { background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 8px 15px; color: #fff; border-radius: 4px; outline: none; }
    input:focus { border-color: var(--primary); }
    button { background: rgba(255,255,255,0.1); border: none; color: #fff; padding: 0 15px; border-radius: 4px; cursor: pointer; }
  }
}

.bill-layout {
  flex: 1; display: flex; gap: 20px; overflow: hidden; margin-top: 20px;
}

.detail-panel { flex: 2; display: flex; flex-direction: column; gap: 20px; overflow-y: auto; }
.card { background: rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; border: 1px solid var(--border); }
.card h3 { font-size: 14px; color: var(--primary); margin-bottom: 10px; }

.table-scroll { max-height: 200px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td, th { text-align: left; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.badge { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #333; }
.badge.High { color: #ff4d4d; background: rgba(255,77,77,0.1); }

.action-panel {
  flex: 1; background: rgba(0,0,0,0.2); padding: 20px; border-radius: 8px;
  display: flex; flex-direction: column; justify-content: space-between;
}
.total-display {
  text-align: right;
  .amount { font-size: 40px; color: #fff; font-weight: 300; margin: 10px 0; small { font-size: 20px; } }
  .breakdown { font-size: 12px; color: var(--text-sec); }
}
.btn-group { display: flex; flex-direction: column; gap: 10px; }
</style>