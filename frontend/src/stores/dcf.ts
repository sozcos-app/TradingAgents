/**
 * DCF 股票估值计算 - Pinia Store
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dcfApi } from '@/api/dcf'
import type {
  DCFValuationResponse,
  CSVValidationResponse,
  FetchFinancialDataResponse,
  ValuateDirectRequest,
  CninfoSearchResponse,
} from '@/types/dcf'

export const useDcfStore = defineStore('dcf', () => {
  // ============ State ============
  const loading = ref(false)
  const result = ref<DCFValuationResponse | null>(null)
  const priceValidation = ref<CSVValidationResponse | null>(null)
  const financialValidation = ref<CSVValidationResponse | null>(null)
  const error = ref<string | null>(null)

  // 自动获取相关
  const fetchedData = ref<FetchFinancialDataResponse | null>(null)
  const fetchLoading = ref(false)

  // 巨潮资讯相关
  const cninfoResults = ref<CninfoSearchResponse | null>(null)
  const cninfoLoading = ref(false)

  // ============ Actions ============

  async function runValuation(params: {
    price_csv: File
    financial_csv: File
    stock_code: string
    model: string
    time?: number
    g1?: number
    g2?: number
    g3?: number
    t1_years?: number
    t2_years?: number
    k_e?: number
  }) {
    loading.value = true
    error.value = null
    result.value = null
    try {
      const res = await dcfApi.valuate(params)
      result.value = (res as any).data || res
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '估值计算失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function runDirectValuation(params: ValuateDirectRequest) {
    loading.value = true
    error.value = null
    result.value = null
    try {
      const res = await dcfApi.valuateDirect(params)
      result.value = (res as any).data || res
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '估值计算失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchFinancialData(stockCode: string, quarters: number = 8) {
    fetchLoading.value = true
    error.value = null
    try {
      const res = await dcfApi.fetchFinancialData({ stock_code: stockCode, quarters })
      fetchedData.value = (res as any).data || res
      return fetchedData.value
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '获取财务数据失败'
      throw e
    } finally {
      fetchLoading.value = false
    }
  }

  async function searchCninfo(stockCode: string, category: string = 'annual') {
    cninfoLoading.value = true
    try {
      const res = await dcfApi.searchCninfo({ stock_code: stockCode, category })
      cninfoResults.value = (res as any).data || res
      return cninfoResults.value
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '搜索公告失败'
      throw e
    } finally {
      cninfoLoading.value = false
    }
  }

  async function validateCsv(file: File, fileType: 'price' | 'financial') {
    try {
      const res = await dcfApi.validateCsv(file, fileType)
      const data = (res as any).data || res
      if (fileType === 'price') {
        priceValidation.value = data as CSVValidationResponse
      } else {
        financialValidation.value = data as CSVValidationResponse
      }
      return data as CSVValidationResponse
    } catch {
      return null
    }
  }

  function clearResult() {
    result.value = null
    error.value = null
    priceValidation.value = null
    financialValidation.value = null
    fetchedData.value = null
    cninfoResults.value = null
  }

  return {
    loading,
    result,
    priceValidation,
    financialValidation,
    error,
    fetchedData,
    fetchLoading,
    cninfoResults,
    cninfoLoading,
    runValuation,
    runDirectValuation,
    fetchFinancialData,
    searchCninfo,
    validateCsv,
    clearResult,
  }
})
