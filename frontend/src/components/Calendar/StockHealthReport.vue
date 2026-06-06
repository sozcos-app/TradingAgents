<template>
  <div class="stock-health-report" v-if="report">
    <!-- 概览卡片 -->
    <el-row :gutter="16" class="overview-section">
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="score-card">
          <div class="score-label">健康度评分</div>
          <div class="score-value" :style="{ color: getScoreColor(report.total_score) }">
            {{ report.total_score }}
          </div>
          <el-progress
            :percentage="report.total_score"
            :color="getScoreColor(report.total_score)"
            :stroke-width="10"
            style="margin-top: 8px;"
          />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="info-card">
          <div class="info-row">
            <span class="info-label">股票</span>
            <span class="info-value">{{ report.stock_name || '-' }} ({{ report.ts_code }})</span>
          </div>
          <div class="info-row">
            <span class="info-label">风险等级</span>
            <el-tag :type="getRiskType(report.risk_level)" size="small">{{ report.risk_level }}</el-tag>
          </div>
          <div class="info-row">
            <span class="info-label">结论</span>
            <el-tag :type="getConclusionType(report.conclusion)" size="small">{{ report.conclusion }}</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="deduction-card">
          <div class="deduction-label">扣分项</div>
          <div class="deduction-value" :class="{ 'has-deduction': report.deduction > 0 }">
            -{{ report.deduction }}分
          </div>
          <div class="deduction-hint" v-if="report.deduction === 0">无扣分</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 五维度评分条 -->
    <el-card shadow="hover" class="dimension-section">
      <div class="dimension-title">五维度评分</div>
      <div class="dimension-list">
        <div class="dimension-item" v-for="dim in dimensions" :key="dim.name">
          <div class="dim-header">
            <span class="dim-name">{{ dim.name }}</span>
            <span class="dim-score">{{ dim.score }}/{{ dim.max }}</span>
          </div>
          <el-progress
            :percentage="(dim.score / dim.max) * 100"
            :color="getDimColor(dim.score, dim.max)"
            :stroke-width="12"
            :text-inside="true"
            :format="() => `${dim.score}/${dim.max}`"
          />
          <div class="dim-detail">{{ dim.detail }}</div>
        </div>
      </div>
    </el-card>

    <!-- 预警列表 -->
    <el-card v-if="report.alerts?.length" shadow="hover" class="alert-section">
      <div class="alert-title">排雷预警</div>
      <el-timeline>
        <el-timeline-item
          v-for="(alert, idx) in report.alerts"
          :key="idx"
          :type="alert.severity === '高' ? 'danger' : 'warning'"
          :hollow="false"
        >
          <div class="alert-item">
            <div class="alert-header">
              <el-tag :type="alert.severity === '高' ? 'danger' : 'warning'" size="small">{{ alert.rule }}</el-tag>
            </div>
            <div class="alert-message">{{ alert.message }}</div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { StockHealthCheck } from '@/types/calendar'

const props = defineProps<{
  report: StockHealthCheck | null
}>()

const dimensions = computed(() => {
  if (!props.report) return []
  return [
    { name: '主营业务匹配度', score: props.report.main_business_score || 0, max: 30, detail: props.report.main_business_detail?.detail || '-' },
    { name: '利润含金量', score: props.report.profit_quality_score || 0, max: 25, detail: props.report.profit_quality_detail?.detail || '-' },
    { name: '毛利率合理性', score: props.report.gross_margin_score || 0, max: 20, detail: props.report.gross_margin_detail?.detail || '-' },
    { name: '信披记录', score: props.report.disclosure_score || 0, max: 15, detail: props.report.disclosure_detail?.detail || '-' },
    { name: '供应链验证', score: props.report.supply_chain_score || 0, max: 10, detail: props.report.supply_chain_detail?.detail || '-' },
  ]
})

function getScoreColor(score: number) {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

function getRiskType(level: string) {
  if (level === '低') return 'success'
  if (level === '中') return 'warning'
  return 'danger'
}

function getConclusionType(c: string) {
  if (c === '可关注') return 'success'
  if (c === '谨慎') return 'warning'
  return 'danger'
}

function getDimColor(score: number, max: number) {
  const pct = score / max
  if (pct >= 0.8) return '#67c23a'
  if (pct >= 0.5) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.stock-health-report { padding: 8px 0; }

.overview-section { margin-bottom: 16px; }

.score-card, .info-card, .deduction-card { min-height: 120px; }

.score-label, .deduction-label { font-size: 13px; color: #909399; margin-bottom: 8px; }

.score-value { font-size: 48px; font-weight: 800; line-height: 1; }

.info-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }

.info-label { font-size: 13px; color: #909399; }
.info-value { font-size: 14px; font-weight: 600; color: #303133; }

.deduction-value { font-size: 36px; font-weight: 700; color: #67c23a; }
.deduction-value.has-deduction { color: #f56c6c; }
.deduction-hint { font-size: 12px; color: #c0c4cc; margin-top: 4px; }

/* 五维度 */
.dimension-section { margin-bottom: 16px; }

.dimension-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 16px; }

.dimension-list { display: flex; flex-direction: column; gap: 14px; }

.dimension-item {
  padding: 4px 0;
}

.dim-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.dim-name { font-size: 13px; color: #606266; }
.dim-score { font-size: 13px; font-weight: 600; color: #303133; }

.dim-detail { font-size: 12px; color: #909399; margin-top: 2px; }

/* 预警 */
.alert-section { margin-bottom: 16px; }

.alert-title { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 12px; }

.alert-item { padding: 2px 0; }
.alert-header { margin-bottom: 4px; }
.alert-message { font-size: 13px; color: #606266; }
</style>
