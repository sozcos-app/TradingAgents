<template>
  <div class="calendar-page">
    <el-tabs v-model="store.activeTab" @tab-change="onTabChange">
      <el-tab-pane label="宏观感知" name="macro">
        <MacroView />
      </el-tab-pane>
      <el-tab-pane label="行业景气" name="industry">
        <IndustryView />
      </el-tab-pane>
      <el-tab-pane label="个股体检" name="stock-health">
        <StockHealthView />
      </el-tab-pane>
      <el-tab-pane label="事件日历" name="events">
        <EventCalendarView />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { useCalendarStore } from '@/stores/calendar'
import MacroView from './MacroView.vue'
import IndustryView from './IndustryView.vue'
import StockHealthView from './StockHealthView.vue'
import EventCalendarView from './EventCalendarView.vue'

const store = useCalendarStore()

function onTabChange(name: string | number) {
  store.activeTab = String(name)
}
</script>

<style scoped>
.calendar-page {
  padding: 20px;
}
</style>
