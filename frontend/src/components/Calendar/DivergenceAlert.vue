<template>
  <div v-if="signal && signal.judgment && signal.judgment !== '暂无数据' && signal.judgment !== '无明显背离'" class="divergence-alert">
    <el-alert
      :title="signal.judgment"
      :type="isLie ? 'error' : isOpportunity ? 'success' : 'warning'"
      show-icon
      :closable="false"
      class="alert-main"
    >
      <div class="alert-body">
        <p class="alert-desc">{{ signal.description }}</p>
        <p class="alert-action">建议: {{ signal.action }}</p>
        <div v-if="signal.signals?.length" class="signal-list">
          <div v-for="(s, idx) in signal.signals" :key="idx" class="signal-item">
            <el-tag :type="s.type === '谎言' ? 'danger' : 'success'" size="small">{{ s.type }}</el-tag>
            <span class="signal-msg">{{ s.message }}</span>
          </div>
        </div>
      </div>
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DivergenceSignal } from '@/types/calendar'

const props = defineProps<{
  signal: DivergenceSignal | null
}>()

const isLie = computed(() => props.signal?.judgment === '谎言风险')
const isOpportunity = computed(() => props.signal?.judgment === '潜在机会')
</script>

<style scoped>
.divergence-alert { margin-bottom: 16px; }

.alert-body {
  margin-top: 8px;
}

.alert-desc {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
}

.alert-action {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.signal-list {
  margin-top: 8px;
}

.signal-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.signal-msg {
  font-size: 12px;
  color: #606266;
}
</style>
