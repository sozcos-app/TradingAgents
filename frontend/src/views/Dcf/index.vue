<template>
  <div class="dcf-view">
    <el-row :gutter="16">
      <!-- 左侧：输入表单 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>DCF 自由现金流折现估值</span>
              <el-button text type="primary" @click="clearAll">清空</el-button>
            </div>
          </template>

          <!-- 数据来源 Tabs -->
          <el-tabs v-model="activeTab" type="border-card">
            <el-tab-pane label="自动获取" name="auto">
              <FinancialDataTable v-model="form.stock_code" />
            </el-tab-pane>

            <el-tab-pane label="上传 CSV" name="csv">
              <el-form
                ref="formRef"
                :model="form"
                :rules="rules"
                label-width="120px"
                label-position="top"
                size="default"
              >
                <!-- 股票代码 -->
                <el-form-item label="股票代码" prop="stock_code">
                  <el-input
                    v-model="form.stock_code"
                    placeholder="例如：sz000977"
                    style="width: 200px"
                  />
                </el-form-item>

                <!-- DCF 模型选择 -->
                <el-form-item label="DCF 模型" prop="model">
                  <el-select v-model="form.model" placeholder="选择估值模型" style="width: 100%">
                    <el-option
                      v-for="opt in DCF_MODEL_OPTIONS"
                      :key="opt.value"
                      :value="opt.value"
                      :label="opt.label"
                    />
                  </el-select>
                </el-form-item>

                <!-- 季度数 -->
                <el-form-item label="数据期数(季度)" prop="time">
                  <el-input-number v-model="form.time" :min="1" :max="20" />
                  <span class="form-hint">使用最近 N 期的财务数据</span>
                </el-form-item>

                <!-- 增长率参数 -->
                <el-divider>模型参数</el-divider>

                <el-form-item
                  v-if="form.model !== 'zero-growth'"
                  label="第一阶段增长率 g1"
                  prop="g1"
                >
                  <el-input-number
                    v-model="form.g1"
                    :precision="4"
                    :step="0.01"
                    :min="-0.5"
                    :max="1"
                  />
                  <span class="form-hint">
                    {{ form.model === 'constant-growth' ? '不变增长率' : '高速增长期增长率' }}
                  </span>
                </el-form-item>

                <el-form-item
                  v-if="form.model === 'two-stage'"
                  label="终值增长率 g2"
                  prop="g2"
                >
                  <el-input-number
                    v-model="form.g2"
                    :precision="4"
                    :step="0.01"
                    :min="-0.5"
                    :max="0.5"
                  />
                  <span class="form-hint">稳定期增长率，应小于 WACC</span>
                </el-form-item>

                <el-form-item
                  v-if="form.model === 'three-stage'"
                  label="过渡期增长率 g2"
                  prop="g2"
                >
                  <el-input-number
                    v-model="form.g2"
                    :precision="4"
                    :step="0.01"
                    :min="-0.5"
                    :max="0.5"
                  />
                </el-form-item>

                <el-form-item
                  v-if="form.model === 'three-stage'"
                  label="终值增长率 g3"
                  prop="g3"
                >
                  <el-input-number
                    v-model="form.g3"
                    :precision="4"
                    :step="0.01"
                    :min="-0.5"
                    :max="0.5"
                  />
                </el-form-item>

                <el-form-item
                  v-if="form.model === 'two-stage' || form.model === 'three-stage'"
                  label="第一阶段年数 t1"
                  prop="t1_years"
                >
                  <el-input-number v-model="form.t1_years" :min="1" :max="10" />
                </el-form-item>

                <el-form-item
                  v-if="form.model === 'three-stage'"
                  label="第二阶段年数 t2"
                  prop="t2_years"
                >
                  <el-input-number v-model="form.t2_years" :min="1" :max="10" />
                </el-form-item>

                <!-- 股权资本成本率 -->
                <el-form-item label="股权资本成本率 k_e" prop="k_e">
                  <el-input-number
                    v-model="form.k_e"
                    :precision="4"
                    :step="0.01"
                    :min="0.01"
                    :max="0.5"
                  />
                  <span class="form-hint">默认 9%</span>
                </el-form-item>

                <!-- CSV 文件上传 -->
                <el-divider>数据文件</el-divider>

                <el-form-item label="价格数据 CSV" prop="price_csv">
                  <el-upload
                    ref="priceUploadRef"
                    drag
                    :auto-upload="false"
                    :limit="1"
                    accept=".csv"
                    :on-change="(file: any) => handlePriceFileChange(file)"
                    :on-remove="handlePriceFileRemove"
                  >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">
                      拖拽或 <em>点击上传</em>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        包含列：股票代码、股票名称、交易日期、总市值、净利润TTM、收盘价
                      </div>
                    </template>
                  </el-upload>
                </el-form-item>

                <el-form-item label="财务数据 CSV" prop="financial_csv">
                  <el-upload
                    ref="financialUploadRef"
                    drag
                    :auto-upload="false"
                    :limit="1"
                    accept=".csv"
                    :on-change="(file: any) => handleFinancialFileChange(file)"
                    :on-remove="handleFinancialFileRemove"
                  >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">
                      拖拽或 <em>点击上传</em>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        财务报表CSV（资产负债表+利润表+现金流量表）
                      </div>
                    </template>
                  </el-upload>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <el-tab-pane label="年报查看" name="report">
              <ReportViewer />
            </el-tab-pane>
          </el-tabs>

          <!-- 估值参数（自动获取模式） -->
          <el-form
            v-if="activeTab === 'auto'"
            ref="autoFormRef"
            :model="form"
            :rules="rules"
            label-width="120px"
            label-position="top"
            size="default"
            style="margin-top: 16px"
          >
            <el-form-item label="股票代码" prop="stock_code">
              <el-input
                v-model="form.stock_code"
                placeholder="例如：sz000977"
                style="width: 200px"
              />
            </el-form-item>

            <el-form-item label="DCF 模型" prop="model">
              <el-select v-model="form.model" placeholder="选择估值模型" style="width: 100%">
                <el-option
                  v-for="opt in DCF_MODEL_OPTIONS"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
            </el-form-item>

            <el-divider>模型参数</el-divider>

            <el-form-item
              v-if="form.model !== 'zero-growth'"
              label="第一阶段增长率 g1"
              prop="g1"
            >
              <el-input-number
                v-model="form.g1"
                :precision="4"
                :step="0.01"
                :min="-0.5"
                :max="1"
              />
            </el-form-item>

            <el-form-item
              v-if="form.model === 'two-stage'"
              label="终值增长率 g2"
              prop="g2"
            >
              <el-input-number
                v-model="form.g2"
                :precision="4"
                :step="0.01"
                :min="-0.5"
                :max="0.5"
              />
            </el-form-item>

            <el-form-item
              v-if="form.model === 'three-stage'"
              label="过渡期增长率 g2"
              prop="g2"
            >
              <el-input-number
                v-model="form.g2"
                :precision="4"
                :step="0.01"
                :min="-0.5"
                :max="0.5"
              />
            </el-form-item>

            <el-form-item
              v-if="form.model === 'three-stage'"
              label="终值增长率 g3"
              prop="g3"
            >
              <el-input-number
                v-model="form.g3"
                :precision="4"
                :step="0.01"
                :min="-0.5"
                :max="0.5"
              />
            </el-form-item>

            <el-form-item
              v-if="form.model === 'two-stage' || form.model === 'three-stage'"
              label="第一阶段年数 t1"
              prop="t1_years"
            >
              <el-input-number v-model="form.t1_years" :min="1" :max="10" />
            </el-form-item>

            <el-form-item
              v-if="form.model === 'three-stage'"
              label="第二阶段年数 t2"
              prop="t2_years"
            >
              <el-input-number v-model="form.t2_years" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="股权资本成本率 k_e" prop="k_e">
              <el-input-number
                v-model="form.k_e"
                :precision="4"
                :step="0.01"
                :min="0.01"
                :max="0.5"
              />
              <span class="form-hint">默认 9%</span>
            </el-form-item>
          </el-form>

          <!-- 提交按钮 -->
          <div style="margin-top: 16px">
            <el-button
              type="primary"
              :loading="store.loading"
              :disabled="!canSubmit"
              @click="handleSubmit"
            >
              开始估值
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：结果展示 -->
      <el-col :xs="24" :lg="12">
        <DcfResults v-if="store.result" />
        <el-card v-else shadow="hover">
          <el-empty description="请获取数据并执行估值计算" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, UploadFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useDcfStore } from '@/stores/dcf'
import { DCF_MODEL_OPTIONS } from '@/types/dcf'
import DcfResults from './DcfResults.vue'
import FinancialDataTable from './FinancialDataTable.vue'
import ReportViewer from './ReportViewer.vue'

const store = useDcfStore()
const formRef = ref<FormInstance>()
const autoFormRef = ref<FormInstance>()
const priceUploadRef = ref()
const financialUploadRef = ref()

const activeTab = ref('auto')

const form = reactive({
  stock_code: '',
  model: 'two-stage' as string,
  time: 4,
  g1: 0.2,
  g2: 0.03,
  g3: 0.01,
  t1_years: 2,
  t2_years: 1,
  k_e: 0.09,
  price_csv: null as File | null,
  financial_csv: null as File | null,
})

const rules = {
  stock_code: [{ required: true, message: '请输入股票代码', trigger: 'blur' }],
  model: [{ required: true, message: '请选择DCF模型', trigger: 'change' }],
}

const canSubmit = computed(() => {
  if (!form.stock_code || !form.model) return false
  if (activeTab.value === 'csv') {
    return form.price_csv && form.financial_csv
  }
  if (activeTab.value === 'auto') {
    return store.fetchedData && store.fetchedData.periods.length > 0
  }
  return false
})

function handlePriceFileChange(file: UploadFile) {
  form.price_csv = file.raw || null
}

function handlePriceFileRemove() {
  form.price_csv = null
}

function handleFinancialFileChange(file: UploadFile) {
  form.financial_csv = file.raw || null
}

function handleFinancialFileRemove() {
  form.financial_csv = null
}

async function handleSubmit() {
  // 自动获取路径
  if (activeTab.value === 'auto') {
    if (!store.fetchedData || store.fetchedData.periods.length === 0) {
      ElMessage.warning('请先获取财务数据')
      return
    }
    const latest = store.fetchedData.periods[0]
    if (!latest.metrics) {
      ElMessage.warning('财务数据指标未计算')
      return
    }
    if (!store.fetchedData.total_market_cap || !store.fetchedData.current_price) {
      ElMessage.warning('缺少市值或价格数据，请手动输入或检查网络')
      return
    }
    if (!store.fetchedData.total_market_cap || store.fetchedData.total_market_cap <= 0) {
      ElMessage.warning('总市值数据异常')
      return
    }
    try {
      await store.runDirectValuation({
        stock_code: form.stock_code,
        stock_name: store.fetchedData.stock_name,
        model: form.model as any,
        time: form.time,
        g1: form.g1,
        g2: form.g2,
        g3: form.g3,
        t1_years: form.t1_years,
        t2_years: form.t2_years,
        k_e: form.k_e,
        metrics: latest.metrics,
        total_market_cap: store.fetchedData.total_market_cap,
        current_price: store.fetchedData.current_price,
      })
      ElMessage.success('估值计算完成')
    } catch {
      ElMessage.error(store.error || '估值计算失败')
    }
    return
  }

  // CSV 上传路径
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请填写必要参数')
    return
  }

  if (!form.price_csv || !form.financial_csv) {
    ElMessage.warning('请上传价格CSV和财务CSV文件')
    return
  }

  try {
    await store.runValuation({
      price_csv: form.price_csv,
      financial_csv: form.financial_csv,
      stock_code: form.stock_code,
      model: form.model,
      time: form.time,
      g1: form.g1,
      g2: form.g2,
      g3: form.g3,
      t1_years: form.t1_years,
      t2_years: form.t2_years,
      k_e: form.k_e,
    })
    ElMessage.success('估值计算完成')
  } catch {
    ElMessage.error(store.error || '估值计算失败')
  }
}

function clearAll() {
  store.clearResult()
  activeTab.value = 'auto'
  form.stock_code = ''
  form.model = 'two-stage'
  form.time = 4
  form.g1 = 0.2
  form.g2 = 0.03
  form.g3 = 0.01
  form.t1_years = 2
  form.t2_years = 1
  form.k_e = 0.09
  form.price_csv = null
  form.financial_csv = null
  priceUploadRef.value?.clearFiles()
  financialUploadRef.value?.clearFiles()
}
</script>

<style lang="scss" scoped>
.dcf-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .form-hint {
    margin-left: 12px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
  }

  :deep(.el-form-item__content) {
    flex-wrap: wrap;
  }
}
</style>
