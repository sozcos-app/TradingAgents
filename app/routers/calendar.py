"""
交易日历 - API 路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.routers.auth_db import get_current_user
from app.core.response import ok
from app.schemas.calendar import (
    MacroIndicatorQuery,
    MacroFetchRequest,
    StockHealthRequest,
    EventQuery,
    EventCreate,
    EventUpdate,
    MarketIndicatorFetchRequest,
    MarketIndicatorHistoryQuery,
    InsightQuery,
)
from app.services.calendar_service import (
    macro_service,
    industry_service,
    stock_health_service,
    event_service,
    market_indicator_service,
)
from app.services.market_insight_service import market_insight_service
from app.models.calendar import EVENT_TYPES

logger = logging.getLogger("webapi")

router = APIRouter(prefix="/calendar", tags=["交易日历"])


# ============ 宏观感知 ============

@router.get("/macro/indicators")
async def get_macro_indicators(current_user: dict = Depends(get_current_user)):
    """获取宏观指标最新值"""
    try:
        data = await macro_service.get_latest_indicators()
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取宏观指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/indicators/{name}")
async def get_indicator_history(
    name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """获取单个指标历史数据"""
    try:
        data = await macro_service.get_indicator_history(name, start_date, end_date, page, page_size)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取指标历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/macro/fetch")
async def fetch_macro_indicators(
    request: MacroFetchRequest = None,
    current_user: dict = Depends(get_current_user),
):
    """手动触发宏观指标采集"""
    try:
        names = request.indicators if request else None
        data = await macro_service.fetch_indicators(names)
        return ok(data=data, message="采集完成")
    except Exception as e:
        logger.error(f"采集宏观指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/macro/score")
async def trigger_macro_score(current_user: dict = Depends(get_current_user)):
    """触发宏观评分计算"""
    try:
        data = await macro_service.calculate_score()
        return ok(data=data, message="评分完成")
    except Exception as e:
        logger.error(f"宏观评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/score/latest")
async def get_macro_score_latest(current_user: dict = Depends(get_current_user)):
    """获取最新宏观评分"""
    try:
        data = await macro_service.get_latest_score()
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取宏观评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/score/history")
async def get_macro_score_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """获取宏观评分历史"""
    try:
        data = await macro_service.get_score_history(start_date, end_date)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取评分历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 行业景气 ============

@router.get("/industry/ranking")
async def get_industry_ranking(current_user: dict = Depends(get_current_user)):
    """获取行业景气排名"""
    try:
        data = await industry_service.get_ranking()
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取行业排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industry/refresh")
async def refresh_industry(current_user: dict = Depends(get_current_user)):
    """刷新全行业数据并评分"""
    try:
        data = await industry_service.refresh_and_score()
        return ok(data=data, message="行业数据刷新完成")
    except Exception as e:
        logger.error(f"刷新行业数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industry/refresh-full")
async def refresh_industry_full(current_user: dict = Depends(get_current_user)):
    """全维度采集并完整评分"""
    try:
        data = await industry_service.refresh_full_score()
        return ok(data=data, message="全维度行业评分完成")
    except Exception as e:
        logger.error(f"全维度行业评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/inventory-cycle-map")
async def get_inventory_cycle_map(current_user: dict = Depends(get_current_user)):
    """获取库存周期象限图数据"""
    try:
        data = await industry_service.get_inventory_cycle_map()
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取库存周期图数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/{name}/detail")
async def get_industry_detail(name: str, current_user: dict = Depends(get_current_user)):
    """获取单行业详情"""
    try:
        data = await industry_service.get_detail(name)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取行业详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/{name}/history")
async def get_industry_history(
    name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """获取单行业评分历史"""
    try:
        data = await industry_service.get_history(name, start_date, end_date)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取行业历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industry/{name}/score")
async def trigger_industry_score(name: str, current_user: dict = Depends(get_current_user)):
    """触发行业评分"""
    try:
        data = await industry_service.calculate_score(name)
        return ok(data=data, message="评分完成")
    except Exception as e:
        logger.error(f"行业评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 个股体检 ============

@router.post("/stock-health/check")
async def check_stock_health(
    request: StockHealthRequest,
    current_user: dict = Depends(get_current_user),
):
    """触发个股体检"""
    try:
        data = await stock_health_service.check_stock(request.ts_code)
        return ok(data=data, message="体检完成")
    except Exception as e:
        logger.error(f"个股体检失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-health/history")
async def get_stock_health_history(
    ts_code: str,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """获取个股体检历史"""
    try:
        data = await stock_health_service.get_history(ts_code, page, page_size)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取体检历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-health/{ts_code}")
async def get_stock_health_report(ts_code: str, current_user: dict = Depends(get_current_user)):
    """获取个股体检报告"""
    try:
        data = await stock_health_service.get_report(ts_code)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取体检报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-health/{ts_code}/alerts")
async def get_stock_health_alerts(ts_code: str, current_user: dict = Depends(get_current_user)):
    """获取个股预警"""
    try:
        data = await stock_health_service.get_alerts(ts_code)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取预警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 市场事件 ============

@router.get("/events")
async def get_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
    impact_direction: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """查询事件列表"""
    try:
        data = await event_service.get_events({
            "start_date": start_date,
            "end_date": end_date,
            "event_type": event_type,
            "impact_direction": impact_direction,
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
        })
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取事件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/upcoming")
async def get_upcoming_events(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
):
    """获取即将到来的事件"""
    try:
        data = await event_service.get_upcoming(days)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取即将到来事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/types")
async def get_event_types(current_user: dict = Depends(get_current_user)):
    """获取事件类型字典"""
    return ok(data=[{"value": v, "label": l} for v, l in EVENT_TYPES])


@router.get("/events/{event_id}")
async def get_event_detail(event_id: str, current_user: dict = Depends(get_current_user)):
    """获取事件详情"""
    try:
        data = await event_service.get_event_by_id(event_id)
        if not data:
            raise HTTPException(status_code=404, detail="事件不存在")
        return ok(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取事件详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
async def create_event(
    request: EventCreate,
    current_user: dict = Depends(get_current_user),
):
    """创建事件"""
    try:
        event_id = await event_service.create_event(
            request.model_dump(),
            created_by=current_user.get("username", "manual"),
        )
        return ok(data={"id": event_id}, message="创建成功")
    except Exception as e:
        logger.error(f"创建事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    request: EventUpdate,
    current_user: dict = Depends(get_current_user),
):
    """更新事件"""
    try:
        update_data = request.model_dump(exclude_none=True)
        success = await event_service.update_event(event_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="事件不存在")
        return ok(message="更新成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """删除事件"""
    try:
        success = await event_service.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="事件不存在")
        return ok(message="删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-days")
async def get_trade_days(
    start_date: str,
    end_date: str,
    current_user: dict = Depends(get_current_user),
):
    """获取交易日列表"""
    try:
        data = await event_service.get_trade_days_api(start_date, end_date)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取交易日失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/fetch")
async def fetch_events(
    start_date: str = "",
    end_date: str = "",
    current_user: dict = Depends(get_current_user),
):
    """手动触发事件采集"""
    try:
        from datetime import timedelta
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
        data = await event_service.fetch_events(start_date, end_date)
        return ok(data=data, message="事件采集完成")
    except Exception as e:
        logger.error(f"事件采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 二级市场指标 ============

@router.get("/macro/market-indicators")
async def get_market_indicators(current_user: dict = Depends(get_current_user)):
    """获取二级市场指标概览"""
    try:
        data = await market_indicator_service.get_latest_overview()
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取二级市场指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/market-indicators/history")
async def get_market_indicators_history(
    indicator_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """获取二级市场指标历史数据"""
    try:
        data = await market_indicator_service.get_history(indicator_type, start_date, end_date, page, page_size)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取二级市场指标历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/divergence")
async def get_divergence_signals(current_user: dict = Depends(get_current_user)):
    """获取最新背离信号"""
    try:
        data = await market_indicator_service.get_latest_divergence()
        if not data:
            return ok(data={"judgment": "暂无数据", "description": "尚未进行背离检测，请先点击检测", "action": "", "signals": []})
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取背离信号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/lie-opportunity")
async def get_lie_opportunity(current_user: dict = Depends(get_current_user)):
    """获取谎言/机会判断（执行一次检测并返回）"""
    try:
        data = await market_indicator_service.detect_divergence()
        return ok(data=data)
    except Exception as e:
        logger.error(f"谎言/机会检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/macro/market-indicators/fetch")
async def fetch_market_indicators(
    request: MarketIndicatorFetchRequest = None,
    current_user: dict = Depends(get_current_user),
):
    """手动触发二级市场指标采集"""
    try:
        types = request.types if request else None
        data = await market_indicator_service.fetch_all_indicators(types)
        return ok(data=data, message="二级市场指标采集完成")
    except Exception as e:
        logger.error(f"采集二级市场指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ AI 洞察分析 ============

@router.post("/macro/insight")
async def analyze_macro_insight(current_user: dict = Depends(get_current_user)):
    """宏观谎言/机会 AI 分析"""
    try:
        data = await market_insight_service.analyze_macro_divergence()
        if "error" in data:
            return ok(data=None, message=data["error"], code=400)
        return ok(data=data, message="分析完成")
    except Exception as e:
        logger.error(f"宏观AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/industry/{name}/insight")
async def analyze_industry_insight(name: str, current_user: dict = Depends(get_current_user)):
    """行业异常 AI 分析"""
    try:
        data = await market_insight_service.analyze_industry_anomaly(name)
        if "error" in data:
            return ok(data=None, message=data["error"], code=400)
        return ok(data=data, message="分析完成")
    except Exception as e:
        logger.error(f"行业AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stock-health/{ts_code}/insight")
async def analyze_stock_insight(ts_code: str, current_user: dict = Depends(get_current_user)):
    """个股风险深度 AI 分析"""
    try:
        data = await market_insight_service.analyze_stock_risk(ts_code)
        if "error" in data:
            return ok(data=None, message=data["error"], code=400)
        return ok(data=data, message="分析完成")
    except Exception as e:
        logger.error(f"个股AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/insight")
async def analyze_event_insight(event_id: str, current_user: dict = Depends(get_current_user)):
    """事件影响 AI 分析"""
    try:
        data = await market_insight_service.analyze_event_impact(event_id)
        if "error" in data:
            return ok(data=None, message=data["error"], code=400)
        return ok(data=data, message="分析完成")
    except Exception as e:
        logger.error(f"事件AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights(
    insight_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """查询历史分析结果"""
    try:
        data = await market_insight_service.get_insights(insight_type, ref_id, limit)
        return ok(data=data)
    except Exception as e:
        logger.error(f"获取洞察历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
