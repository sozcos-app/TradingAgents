"""DCF 股票估值计算 - API 路由"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.dcf import (
    DCFModel,
    DCFValuationResponse,
    CSVValidationResponse,
    FetchFinancialDataResponse,
    ValuateDirectRequest,
    CninfoSearchResponse,
)
from app.services.dcf_service import run_valuation, validate_csv, run_valuation_direct
from app.services.dcf_data_fetch_service import DcfDataFetchService
from app.services.cninfo_service import cninfo_service

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/dcf", tags=["DCF估值计算"])


@router.post("/valuate", response_model=DCFValuationResponse, summary="执行DCF估值计算")
async def valuate(
    price_csv: UploadFile = File(..., description="股票价格CSV文件"),
    financial_csv: UploadFile = File(..., description="财务数据CSV文件"),
    stock_code: str = Form(..., description="股票代码，如 sz000977"),
    model: DCFModel = Form(..., description="DCF模型: zero-growth / constant-growth / two-stage / three-stage"),
    time: int = Form(default=4, description="采用最近n期的数据(季度)"),
    g1: float = Form(default=0.2, description="第一阶段增长率"),
    g2: float = Form(default=0.03, description="第二阶段增长率(两阶段模型终值增长率)"),
    g3: float = Form(default=0.01, description="第三阶段增长率(三阶段模型终值增长率)"),
    t1_years: int = Form(default=2, description="第一阶段年数"),
    t2_years: int = Form(default=1, description="第二阶段年数(三阶段模型)"),
    k_e: float = Form(default=0.09, description="股权资本成本率"),
):
    """
    接收2个CSV文件 + 表单参数，执行DCF估值计算。

    - **price_csv**: 价格CSV（列：股票代码/股票名称/交易日期/总市值/净利润TTM/收盘价）
    - **financial_csv**: 财务CSV（资产负债表+利润表+现金流量表）
    - **model**: zero-growth / constant-growth / two-stage / three-stage
    """
    try:
        price_content = await price_csv.read()
        financial_content = await financial_csv.read()

        result = run_valuation(
            price_csv=price_content,
            financial_csv=financial_content,
            stock_code=stock_code,
            model=model,
            time=time,
            g1=g1,
            g2=g2,
            g3=g3,
            t1_years=t1_years,
            t2_years=t2_years,
            k_e=k_e,
        )
        return result
    except ValueError as e:
        logger.warning(f"DCF估值参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DCF估值计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"估值计算失败: {str(e)}")


@router.post("/validate-csv", response_model=CSVValidationResponse, summary="校验CSV格式")
async def validate_csv_endpoint(
    file: UploadFile = File(..., description="CSV文件"),
    file_type: str = Form(..., description="文件类型: price / financial"),
):
    """校验上传的CSV文件格式是否满足要求"""
    try:
        content = await file.read()
        result = validate_csv(content, file_type, file.filename or "")
        return result
    except Exception as e:
        logger.error(f"CSV校验失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"CSV校验失败: {str(e)}")


@router.post("/fetch-financial-data", response_model=FetchFinancialDataResponse, summary="自动获取财务数据")
async def fetch_financial_data(
    stock_code: str = Form(..., description="股票代码，如 002138"),
    quarters: int = Form(default=8, description="获取最近N个报告期"),
):
    """通过 AKShare 自动获取财务数据，返回多期财务报表和计算后的指标"""
    try:
        service = DcfDataFetchService()
        result = await service.fetch_financial_data(stock_code, quarters)
        return result
    except ValueError as e:
        logger.warning(f"获取财务数据参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取财务数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取财务数据失败: {str(e)}")


@router.post("/valuate-direct", response_model=DCFValuationResponse, summary="直接估值（跳过CSV）")
async def valuate_direct(request: ValuateDirectRequest):
    """接收预计算的财务指标和价格数据，直接执行 DCF 估值"""
    try:
        result = run_valuation_direct(request)
        return result
    except ValueError as e:
        logger.warning(f"直接估值参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"直接估值计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"估值计算失败: {str(e)}")


@router.post("/cninfo-search", response_model=CninfoSearchResponse, summary="搜索巨潮资讯公告")
async def cninfo_search(
    stock_code: str = Form(..., description="股票代码，如 002138"),
    category: str = Form(default="annual", description="公告类型: annual/quarter1/semi/quarter3"),
):
    """搜索巨潮资讯公告（年报/季报/半年报）"""
    try:
        result = await cninfo_service.search_announcements(stock_code, category)
        return result
    except Exception as e:
        logger.error(f"巨潮资讯搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索公告失败: {str(e)}")


@router.get("/history", summary="查询估值历史记录")
async def get_history(
    stock_code: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """查询历史估值记录（预留接口，暂返回空列表）"""
    return {
        "total": 0,
        "page": page,
        "page_size": page_size,
        "items": [],
    }
