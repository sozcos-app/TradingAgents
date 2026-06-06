<template>
  <div class="ai-insight-card">
    <div class="insight-header">
      <div class="insight-tags">
        <el-tag :type="typeTagMap[type] || 'info'" size="small">{{ typeLabels[type] || type }}</el-tag>
        <el-tag
          v-if="judgmentTag"
          :type="judgmentTag.type"
          size="small"
          effect="dark"
        >{{ judgmentTag.label }}</el-tag>
      </div>
      <span v-if="time" class="insight-time">{{ time }}</span>
    </div>
    <div class="insight-content" v-html="renderedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
  type: string
  time?: string
}>()

const typeTagMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
  macro: 'primary',
  industry: 'success',
  stock: 'warning',
  event: 'danger',
}

const typeLabels: Record<string, string> = {
  macro: '宏观分析',
  industry: '行业分析',
  stock: '个股分析',
  event: '事件分析',
}

type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

const judgmentTag = computed<{ label: string; type: TagType } | null>(() => {
  const c = props.content
  if (c.includes('谎言') || c.includes('虚假繁荣') || c.includes('虚高')) {
    return { label: '谎言信号', type: 'danger' }
  }
  if (c.includes('机会') || c.includes('被低估') || c.includes('缩量见底')) {
    return { label: '机会信号', type: 'success' }
  }
  if (c.includes('利多') || c.includes('受益')) {
    return { label: '利多', type: 'success' }
  }
  if (c.includes('利空') || c.includes('回避')) {
    return { label: '利空', type: 'danger' }
  }
  return null
})

const renderedContent = computed(() => {
  try {
    return marked.parse(props.content || '') as string
  } catch {
    return props.content
  }
})
</script>

<style scoped>
.ai-insight-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
}

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.insight-tags {
  display: flex;
  gap: 6px;
}

.insight-time {
  font-size: 12px;
  color: #909399;
}

.insight-content {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}

.insight-content :deep(h1),
.insight-content :deep(h2),
.insight-content :deep(h3) {
  margin: 12px 0 6px;
  font-size: 15px;
  font-weight: 600;
}

.insight-content :deep(ul),
.insight-content :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.insight-content :deep(p) {
  margin: 4px 0;
}

.insight-content :deep(strong) {
  color: #409eff;
}
</style>
