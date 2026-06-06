<template>
  <div class="event-calendar-view">
    <!-- 顶部操作栏 -->
    <div class="event-header">
      <div class="header-left">
        <el-button @click="prevMonth">&lt;</el-button>
        <span class="month-label">{{ currentYear }}年{{ currentMonth }}月</span>
        <el-button @click="nextMonth">&gt;</el-button>
      </div>
      <div class="header-right">
        <el-select v-model="filterType" placeholder="事件类型" clearable size="small" style="width: 120px;">
          <el-option v-for="t in eventTypes" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button size="small" :loading="fetchingEvents" @click="handleFetchEvents">采集事件</el-button>
        <el-button type="primary" size="small" @click="openAddDialog">添加事件</el-button>
      </div>
    </div>

    <!-- 日历网格 -->
    <div class="calendar-grid">
      <div class="weekday-header">
        <div v-for="d in weekdays" :key="d" class="weekday-cell">{{ d }}</div>
      </div>
      <div class="date-grid">
        <div
          v-for="(cell, idx) in calendarCells"
          :key="idx"
          class="date-cell"
          :class="{
            'other-month': !cell.isCurrentMonth,
            'today': cell.isToday,
            'selected': cell.date === selectedDate,
            'non-trade-day': !cell.isCurrentMonth ? false : !isTradeDay(cell.date),
          }"
          @click="selectDate(cell.date)"
        >
          <div class="date-number">{{ cell.day }}</div>
          <div class="event-dots">
            <span
              v-for="evt in getEventsForDate(cell.date)"
              :key="evt.id"
              class="event-dot"
              :class="'impact-' + evt.impact_direction"
            ></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 选中日期的事件列表 -->
    <div class="event-list" v-if="selectedDateEvents.length">
      <h4>{{ selectedDate }} 事件</h4>
      <el-card v-for="evt in selectedDateEvents" :key="evt.id" shadow="hover" class="event-card">
        <div class="event-card-header">
          <el-tag :type="getImpactType(evt.impact_direction)" size="small">{{ evt.impact_direction }}</el-tag>
          <span class="event-title">{{ evt.title }}</span>
          <el-tag size="small" type="info">{{ evt.event_type }}</el-tag>
        </div>
        <div class="event-meta">
          <span v-if="evt.impact_strength">强度: {{ evt.impact_strength }}</span>
          <span v-if="evt.affected_sectors?.length">板块: {{ evt.affected_sectors.join(', ') }}</span>
        </div>
        <div v-if="evt.action_suggestion" class="event-suggestion">{{ evt.action_suggestion }}</div>
        <div class="event-card-actions">
          <el-button type="primary" link size="small" @click="openDetailDialog(evt)">详情</el-button>
          <el-button type="warning" link size="small" @click="openEditDialog(evt)">编辑</el-button>
          <el-popconfirm title="确认删除该事件？" @confirm="handleDeleteEvent(evt.id!)">
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </el-card>
    </div>

    <!-- 事件详情弹窗 -->
    <el-dialog v-model="showDetailDialog" title="事件详情" width="560px">
      <template v-if="detailEvent">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题" :span="2">{{ detailEvent.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ detailEvent.event_type }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ detailEvent.event_date?.substring(0, 10) }}</el-descriptions-item>
          <el-descriptions-item label="影响方向">
            <el-tag :type="getImpactType(detailEvent.impact_direction)" size="small">{{ detailEvent.impact_direction }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="影响强度">
            <el-tag size="small">{{ detailEvent.impact_strength }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="影响板块" :span="2">
            <template v-if="detailEvent.affected_sectors?.length">
              <el-tag v-for="s in detailEvent.affected_sectors" :key="s" size="small" style="margin-right: 4px;">{{ s }}</el-tag>
            </template>
            <span v-else>无</span>
          </el-descriptions-item>
          <el-descriptions-item label="操作建议" :span="2">
            {{ detailEvent.action_suggestion || '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="来源" :span="2">{{ detailEvent.source || '手动' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detailEvent.description || '无' }}</el-descriptions-item>
          <el-descriptions-item label="创建方式">{{ detailEvent.is_auto ? '自动采集' : '手动添加' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailEvent.created_by || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- AI 分析 -->
        <div style="margin-top: 16px;">
          <el-button type="primary" :loading="insightLoading" @click="handleEventInsight">
            AI 事件影响分析
          </el-button>
          <AiInsightCard
            v-if="eventInsight"
            :content="eventInsight"
            type="event"
          />
        </div>
      </template>
    </el-dialog>

    <!-- 添加事件弹窗 -->
    <el-dialog v-model="showAddDialog" title="添加事件" width="500px" @close="resetEventForm">
      <el-form :model="eventForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="eventForm.title" placeholder="事件标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="eventForm.event_type" style="width: 100%;">
            <el-option v-for="t in eventTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="eventForm.event_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="影响方向">
          <el-radio-group v-model="eventForm.impact_direction">
            <el-radio value="利多">利多</el-radio>
            <el-radio value="利空">利空</el-radio>
            <el-radio value="中性">中性</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="影响强度">
          <el-radio-group v-model="eventForm.impact_strength">
            <el-radio value="高">高</el-radio>
            <el-radio value="中">中</el-radio>
            <el-radio value="低">低</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="影响板块">
          <el-select v-model="eventForm.affected_sectors" multiple filterable allow-create placeholder="输入或选择板块" style="width: 100%;">
          </el-select>
        </el-form-item>
        <el-form-item label="建议">
          <el-input v-model="eventForm.action_suggestion" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="eventForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddEvent">确认</el-button>
      </template>
    </el-dialog>

    <!-- 编辑事件弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑事件" width="500px">
      <template v-if="editingEvent">
        <el-form :model="editingEvent" label-width="80px">
          <el-form-item label="标题" required>
            <el-input v-model="editingEvent.title" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="editingEvent.event_type" style="width: 100%;">
              <el-option v-for="t in eventTypes" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" required>
            <el-date-picker v-model="editingEvent.event_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
          </el-form-item>
          <el-form-item label="影响方向">
            <el-radio-group v-model="editingEvent.impact_direction">
              <el-radio value="利多">利多</el-radio>
              <el-radio value="利空">利空</el-radio>
              <el-radio value="中性">中性</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="影响强度">
            <el-radio-group v-model="editingEvent.impact_strength">
              <el-radio value="高">高</el-radio>
              <el-radio value="中">中</el-radio>
              <el-radio value="低">低</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="影响板块">
            <el-select v-model="editingEvent.affected_sectors" multiple filterable allow-create placeholder="输入或选择板块" style="width: 100%;">
            </el-select>
          </el-form-item>
          <el-form-item label="建议">
            <el-input v-model="editingEvent.action_suggestion" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editingEvent.description" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUpdateEvent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useCalendarStore } from '@/stores/calendar'
import { calendarApi } from '@/api/calendar'
import type { MarketEvent } from '@/types/calendar'
import { ElMessage } from 'element-plus'
import AiInsightCard from '@/components/Calendar/AiInsightCard.vue'

const store = useCalendarStore()
const weekdays = ['一', '二', '三', '四', '五', '六', '日']

const currentYear = ref(new Date().getFullYear())
const currentMonth = ref(new Date().getMonth() + 1)
const selectedDate = ref('')
const filterType = ref('')
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showDetailDialog = ref(false)
const eventTypes = ref<{ value: string; label: string }[]>([])
const tradeDays = ref<Set<string>>(new Set())
const fetchingEvents = ref(false)
const submitting = ref(false)
const detailEvent = ref<MarketEvent | null>(null)
const editingEvent = ref<Partial<MarketEvent> | null>(null)
const eventInsight = ref('')
const insightLoading = ref(false)

const eventForm = ref({
  title: '',
  event_type: '其他',
  event_date: '',
  impact_direction: '中性',
  impact_strength: '低',
  action_suggestion: '',
  description: '',
  affected_sectors: [] as string[],
})

// 日历格子
const calendarCells = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const daysInMonth = lastDay.getDate()

  let startWeekday = firstDay.getDay() - 1
  if (startWeekday < 0) startWeekday = 6

  const cells = []
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  const prevMonthDays = new Date(year, month - 1, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = prevMonthDays - i
    const m = month === 1 ? 12 : month - 1
    const y = month === 1 ? year - 1 : year
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: dateStr, isCurrentMonth: false, isToday: dateStr === todayStr })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: dateStr, isCurrentMonth: true, isToday: dateStr === todayStr })
  }

  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    const m = month === 12 ? 1 : month + 1
    const y = month === 12 ? year + 1 : year
    const dateStr = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: dateStr, isCurrentMonth: false, isToday: dateStr === todayStr })
  }

  return cells
})

// 日期事件映射
const eventMap = computed(() => {
  const map: Record<string, MarketEvent[]> = {}
  for (const evt of store.events) {
    const d = evt.event_date?.substring(0, 10) || ''
    if (!map[d]) map[d] = []
    map[d].push(evt)
  }
  return map
})

function getEventsForDate(dateStr: string) {
  let events = eventMap.value[dateStr] || []
  if (filterType.value) {
    events = events.filter(e => e.event_type === filterType.value)
  }
  return events
}

const selectedDateEvents = computed(() => {
  if (!selectedDate.value) return []
  return getEventsForDate(selectedDate.value)
})

function isTradeDay(dateStr: string): boolean {
  // 如果没有交易日数据，默认所有工作日都算交易日（跳过周末）
  if (tradeDays.value.size === 0) {
    const d = new Date(dateStr)
    return d.getDay() !== 0 && d.getDay() !== 6
  }
  return tradeDays.value.has(dateStr)
}

function selectDate(dateStr: string) {
  selectedDate.value = dateStr
}

function prevMonth() {
  if (currentMonth.value === 1) {
    currentMonth.value = 12
    currentYear.value--
  } else {
    currentMonth.value--
  }
}

function nextMonth() {
  if (currentMonth.value === 12) {
    currentMonth.value = 1
    currentYear.value++
  } else {
    currentMonth.value++
  }
}

function getImpactType(direction: string) {
  if (direction === '利多') return 'success'
  if (direction === '利空') return 'danger'
  return 'info'
}

function resetEventForm() {
  eventForm.value = {
    title: '',
    event_type: '其他',
    event_date: '',
    impact_direction: '中性',
    impact_strength: '低',
    action_suggestion: '',
    description: '',
    affected_sectors: [],
  }
}

function openAddDialog() {
  resetEventForm()
  if (selectedDate.value) {
    eventForm.value.event_date = selectedDate.value
  }
  showAddDialog.value = true
}

function openDetailDialog(evt: MarketEvent) {
  detailEvent.value = evt
  eventInsight.value = ''
  showDetailDialog.value = true
}

function openEditDialog(evt: MarketEvent) {
  editingEvent.value = { ...evt }
  showEditDialog.value = true
}

async function handleEventInsight() {
  if (!detailEvent.value?.id) return
  insightLoading.value = true
  eventInsight.value = ''
  try {
    const res = await calendarApi.insight.analyzeEvent(detailEvent.value.id)
    eventInsight.value = res.data?.content || ''
    if (!eventInsight.value) {
      ElMessage.warning(res.message || '分析结果为空')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || 'AI分析失败')
  } finally {
    insightLoading.value = false
  }
}

async function handleAddEvent() {
  if (!eventForm.value.title || !eventForm.value.event_date) {
    ElMessage.warning('请填写标题和日期')
    return
  }
  submitting.value = true
  try {
    await calendarApi.events.create(eventForm.value)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    loadEvents()
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  } finally {
    submitting.value = false
  }
}

async function handleUpdateEvent() {
  if (!editingEvent.value?.id) return
  submitting.value = true
  try {
    const { id, ...data } = editingEvent.value
    await calendarApi.events.update(id, data)
    ElMessage.success('更新成功')
    showEditDialog.value = false
    editingEvent.value = null
    loadEvents()
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

async function handleDeleteEvent(id: string) {
  try {
    await calendarApi.events.delete(id)
    ElMessage.success('删除成功')
    loadEvents()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

async function handleFetchEvents() {
  fetchingEvents.value = true
  try {
    const year = currentYear.value
    const month = currentMonth.value
    const start = `${year}-${String(month).padStart(2, '0')}-01`
    const endMonth = month === 12 ? 1 : month + 1
    const endYear = month === 12 ? year + 1 : year
    const end = `${endYear}-${String(endMonth).padStart(2, '0')}-01`
    const res = await calendarApi.events.fetchEvents(start, end)
    const count = res.data?.results ? Object.values(res.data.results).reduce((a: number, b: any) => a + (b as number), 0) : 0
    ElMessage.success(`采集完成，共采集 ${count} 条事件`)
    loadEvents()
  } catch (e: any) {
    ElMessage.error(e?.message || '采集失败')
  } finally {
    fetchingEvents.value = false
  }
}

async function loadEvents() {
  const year = currentYear.value
  const month = currentMonth.value
  const start = `${year}-${String(month).padStart(2, '0')}-01`
  const endMonth = month === 12 ? 1 : month + 1
  const endYear = month === 12 ? year + 1 : year
  const end = `${endYear}-${String(endMonth).padStart(2, '0')}-01`
  await store.fetchEvents({ start_date: start, end_date: end, page_size: 200 })
}

async function loadTradeDays() {
  try {
    const year = currentYear.value
    const month = currentMonth.value
    const start = `${year}-${String(month).padStart(2, '0')}-01`
    const endMonth = month === 12 ? 1 : month + 1
    const endYear = month === 12 ? year + 1 : year
    const end = `${endYear}-${String(endMonth).padStart(2, '0')}-01`
    const res = await calendarApi.events.getTradeDays(start, end)
    const days: string[] = res.data || []
    tradeDays.value = new Set(days.map(d => d.substring(0, 10)))
  } catch {
    // 交易日加载失败不影响核心功能
  }
}

watch([currentYear, currentMonth], () => {
  loadEvents()
  loadTradeDays()
})

onMounted(async () => {
  try {
    const res = await calendarApi.events.getTypes()
    eventTypes.value = res.data || []
  } catch {}
  loadEvents()
  loadTradeDays()
})
</script>

<style scoped>
.event-calendar-view { padding: 16px 0; }

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left { display: flex; align-items: center; gap: 12px; }
.month-label { font-size: 18px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }

/* 日历网格 */
.calendar-grid { margin-bottom: 20px; }

.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-weight: 600;
  color: #606266;
  margin-bottom: 4px;
}

.weekday-cell { padding: 8px 0; }

.date-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.date-cell {
  min-height: 60px;
  padding: 4px;
  border: 1px solid #f0f0f0;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.date-cell:hover { background: #f5f7fa; }
.date-cell.other-month { opacity: 0.4; }
.date-cell.today { border-color: #409eff; }
.date-cell.selected { background: #ecf5ff; }
.date-cell.non-trade-day { background: #fafafa; }
.date-cell.non-trade-day .date-number { color: #c0c4cc; text-decoration: line-through; }

.date-number { font-size: 13px; color: #303133; margin-bottom: 4px; }

.event-dots { display: flex; gap: 2px; flex-wrap: wrap; }

.event-dot {
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block;
}

.impact-利多 { background: #67c23a; }
.impact-利空 { background: #f56c6c; }
.impact-中性 { background: #909399; }

/* 事件列表 */
.event-list h4 { margin-bottom: 12px; color: #303133; }

.event-card { margin-bottom: 8px; }

.event-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.event-title { font-weight: 600; flex: 1; }

.event-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 16px;
}

.event-suggestion {
  margin-top: 6px;
  font-size: 13px;
  color: #606266;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.event-card-actions {
  margin-top: 8px;
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}
</style>
