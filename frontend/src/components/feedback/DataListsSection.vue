<!-- components/feedback/DataListsSection.vue -->
<template>
  <div class="data-lists">
    <div class="data-grid">
      <!-- 违规类型统计 -->
      <div class="data-panel">
        <div class="panel-header">违规类型统计</div>
        <div class="panel-body">
          <div v-if="violationsList.length === 0" class="empty-state">
            <div class="loading-spinner"></div>
            <div>加载中...</div>
          </div>
          <ul v-else class="data-list">
            <li v-for="item in violationsList" :key="item.type" class="list-item">
              <div class="item-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-desc">安全违规检测</div>
              </div>
              <div class="item-count violation-count">{{ item.count }}</div>
            </li>
          </ul>
        </div>
      </div>

      <!-- 摄像头统计 -->
      <div class="data-panel">
        <div class="panel-header">摄像头统计</div>
        <div class="panel-body">
          <div v-if="camerasList.length === 0" class="empty-state">
            <div class="loading-spinner"></div>
            <div>加载中...</div>
          </div>
          <ul v-else class="data-list">
            <li v-for="item in camerasList" :key="item.camera_id" class="list-item">
              <div class="item-info">
                <div class="item-name">{{ item.camera_id }}</div>
                <div class="item-desc">违规检测摄像头</div>
              </div>
              <div class="item-count">{{ item.violations }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DataListsSection',
  props: {
    violationsList: {
      type: Array,
      default: () => []
    },
    camerasList: {
      type: Array,
      default: () => []
    }
  }
}
</script>

<style scoped>
.data-lists {
  margin-bottom: 40px;
}

.data-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
}

.data-panel {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  overflow: hidden;
}

.panel-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 25px;
  font-size: 1.2em;
  font-weight: 600;
}

.panel-body {
  padding: 25px;
}

.data-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px;
  margin-bottom: 12px;
  background: #f8f9fa;
  border-radius: 10px;
  border-left: 4px solid #667eea;
  transition: all 0.3s ease;
}

.list-item:hover {
  background: #e9ecef;
  transform: translateX(5px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.list-item:last-child {
  margin-bottom: 0;
}

.item-info {
  display: flex;
  flex-direction: column;
}

.item-name {
  font-weight: 600;
  color: #495057;
  margin-bottom: 4px;
  font-size: 1.05em;
}

.item-desc {
  font-size: 0.85em;
  color: #6c757d;
}

.item-count {
  background: #667eea;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.95em;
  font-weight: 600;
  min-width: 50px;
  text-align: center;
}

.violation-count {
  background: #dc3545;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #6c757d;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f4f6;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-grid {
    grid-template-columns: 1fr;
  }
}
</style>