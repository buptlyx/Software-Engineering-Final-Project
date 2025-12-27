<template>
  <div class="glass-container full-height">
    <header class="section-header">
      <h3><BarChart3 :size="24" /> 统计报表</h3>
      <button class="neon-btn outline" @click="fetchData">刷新数据</button>
    </header>

    <div v-if="loading" class="loading-state">
      <Loader2 class="spin" :size="40" />
      <p>正在加载统计数据...</p>
    </div>

    <div v-else class="report-content">
      <!-- 关键指标卡片 -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="label">总收入</div>
          <div class="value">¥{{ formatNumber(data.total_income) }}</div>
          <div class="sub-text">含房费、空调、餐饮</div>
        </div>
        <div class="kpi-card">
          <div class="label">总入住次数</div>
          <div class="value">{{ data.total_check_ins }}</div>
          <div class="sub-text">累计接待</div>
        </div>
        <div class="kpi-card">
          <div class="label">空调总费用</div>
          <div class="value">¥{{ formatNumber(data.total_ac_fee) }}</div>
          <div class="sub-text">运行时长 {{ (data.total_ac_duration / 60).toFixed(0) }} 分钟</div>
        </div>
        <div class="kpi-card">
          <div class="label">餐饮总收入</div>
          <div class="value">¥{{ formatNumber(data.total_food_fee) }}</div>
          <div class="sub-text">额外服务</div>
        </div>
      </div>

      <!-- 收入构成可视化 (简单的 CSS 条形图) -->
      <div class="chart-section">
        <h4>收入构成分析</h4>
        <div class="bar-chart-container">
          <div class="bar-row">
            <span class="bar-label">房费</span>
            <div class="bar-track">
              <div class="bar-fill primary" :style="{ width: getPercent(data.total_stay_fee) + '%' }"></div>
            </div>
            <span class="bar-value">¥{{ formatNumber(data.total_stay_fee) }} ({{ getPercent(data.total_stay_fee) }}%)</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">空调费</span>
            <div class="bar-track">
              <div class="bar-fill warning" :style="{ width: getPercent(data.total_ac_fee) + '%' }"></div>
            </div>
            <span class="bar-value">¥{{ formatNumber(data.total_ac_fee) }} ({{ getPercent(data.total_ac_fee) }}%)</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">餐饮费</span>
            <div class="bar-track">
              <div class="bar-fill success" :style="{ width: getPercent(data.total_food_fee) + '%' }"></div>
            </div>
            <span class="bar-value">¥{{ formatNumber(data.total_food_fee) }} ({{ getPercent(data.total_food_fee) }}%)</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { BarChart3, Loader2 } from 'lucide-vue-next';

const loading = ref(true);
const data = ref({
  total_income: 0,
  total_stay_fee: 0,
  total_ac_fee: 0,
  total_food_fee: 0,
  total_check_ins: 0,
  total_ac_duration: 0
});

const formatNumber = (num) => {
  return num ? num.toFixed(2) : '0.00';
};

const getPercent = (val) => {
  if (!data.value.total_income) return 0;
  return ((val / data.value.total_income) * 100).toFixed(1);
};

const fetchData = async () => {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:5000/api/report');
    if (response.ok) {
      data.value = await response.json();
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchData);
</script>

<style scoped lang="scss">
@import '../common-panel.css';

.glass-container {
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  h3 { display: flex; align-items: center; gap: 10px; font-size: 24px; color: var(--primary); }
}

.loading-state {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--primary);
  .spin { animation: spin 1s linear infinite; margin-bottom: 15px; }
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.report-content {
  flex: 1;
  overflow-y: auto;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.kpi-card {
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex; flex-direction: column;
  transition: transform 0.2s;
  
  &:hover { transform: translateY(-5px); border-color: var(--primary); }

  .label { color: var(--text-sec); font-size: 14px; margin-bottom: 10px; }
  .value { font-size: 32px; font-weight: bold; color: #fff; margin-bottom: 5px; }
  .sub-text { font-size: 12px; color: rgba(255,255,255,0.4); }
}

.chart-section {
  background: rgba(0,0,0,0.2);
  border-radius: 12px;
  padding: 25px;
  border: 1px solid var(--border);
  
  h4 { margin-bottom: 20px; color: #fff; font-weight: normal; }
}

.bar-chart-container {
  display: flex; flex-direction: column; gap: 15px;
}

.bar-row {
  display: flex; align-items: center; gap: 15px;
  .bar-label { width: 80px; text-align: right; color: var(--text-sec); font-size: 14px; }
  .bar-track { 
    flex: 1; height: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; overflow: hidden; 
  }
  .bar-fill { height: 100%; border-radius: 6px; transition: width 1s ease; }
  .bar-value { width: 150px; font-size: 14px; color: #fff; }
  
  .primary { background: var(--primary); }
  .warning { background: #ff9d00; }
  .success { background: #00ff9d; }
}
</style>
