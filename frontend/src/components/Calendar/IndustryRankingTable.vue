<template>
  <el-table :data="ranking" stripe style="width: 100%;" row-key="industry_name" @row-click="handleRowClick">
    <el-table-column type="index" label="排名" width="60">
      <template #default="{ $index }">{{ $index + 1 }}</template>
    </el-table-column>
    <el-table-column prop="industry_name" label="行业" width="120" />
    <el-table-column label="景气评分" width="200" sortable :sort-method="sortByScore">
      <template #default="{ row }">
        <el-progress
          :percentage="row.score"
          :color="getScoreColor(row.score)"
          :stroke-width="14"
          :text-inside="true"
          :format="() => row.score + '分'"
        />
      </template>
    </el-table-column>
    <el-table-column label="配置建议" width="100">
      <template #default="{ row }">
        <el-tag :type="getSuggestionType(row.suggestion)" size="small">{{ row.suggestion }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="库存周期" width="100">
      <template #default="{ row }">{{ row.inventory_cycle || '-' }}</template>
    </el-table-column>
    <el-table-column label="涨跌幅" width="100">
      <template #default="{ row }">
        <span :style="{ color: getChangeColor(row.change_pct) }">
          {{ row.change_pct?.toFixed(2) ?? '-' }}%
        </span>
      </template>
    </el-table-column>
    <el-table-column label="换手率" width="80">
      <template #default="{ row }">{{ row.turnover_rate?.toFixed(2) ?? '-' }}%</template>
    </el-table-column>
    <el-table-column label="催化剂" min-width="180">
      <template #default="{ row }">
        <el-tag v-for="(c, idx) in (row.catalysts || []).slice(0, 3)" :key="idx" size="small" type="info" style="margin-right: 4px; margin-bottom: 2px;">
          {{ c }}
        </el-tag>
        <span v-if="!row.catalysts?.length" style="color: #c0c4cc;">-</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="80" fixed="right">
      <template #default="{ row }">
        <el-button size="small" link type="primary" @click.stop="$emit('showDetail', row.industry_name)">详情</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { IndustryProsperity } from '@/types/calendar'

defineProps<{
  ranking: IndustryProsperity[]
}>()

defineEmits<{
  showDetail: [name: string]
}>()

function handleRowClick(_row: IndustryProsperity) {
  // row click handler
}

function sortByScore(a: IndustryProsperity, b: IndustryProsperity): number {
  return (a.score || 0) - (b.score || 0)
}

function getScoreColor(score: number) {
  if (score >= 70) return '#67c23a'
  if (score >= 50) return '#e6a23c'
  return '#f56c6c'
}

function getSuggestionType(s: string) {
  if (s === '超配') return 'success'
  if (s === '标配') return 'warning'
  return 'danger'
}

function getChangeColor(val?: number) {
  if (!val) return '#909399'
  return val > 0 ? '#f56c6c' : val < 0 ? '#67c23a' : '#909399'
}
</script>
