"""
交易日历 - 请求/响应 Schema
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 宏观指标 ============

class MacroIndicatorQuery(BaseModel):
    """宏观指标查询参数"""
    indicator_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MacroFetchRequest(BaseModel):
    """手动采集请求"""
    indicators: Optional[List[str]] = Field(default=None, description="不传则采集全部")


class MacroScoreResponse(BaseModel):
    """宏观评分响应"""
    total_score: float
    level: str
    details: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    date: str


# ============ 行业景气 ============

class IndustryQuery(BaseModel):
    """行业查询参数"""
    keyword: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============ 个股体检 ============

class StockHealthRequest(BaseModel):
    """个股体检请求"""
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")


# ============ 市场事件 ============

class EventQuery(BaseModel):
    """事件查询参数"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    event_type: Optional[str] = None
    impact_direction: Optional[str] = None
    keyword: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class EventCreate(BaseModel):
    """创建事件"""
    title: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(..., description="事件类型")
    event_date: str = Field(..., description="事件日期 YYYY-MM-DD")
    impact_direction: Optional[str] = Field(default="中性")
    impact_strength: Optional[str] = Field(default="低")
    affected_sectors: Optional[List[str]] = Field(default_factory=list)
    action_suggestion: Optional[str] = Field(default="")
    source: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")


class EventUpdate(BaseModel):
    """更新事件"""
    title: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[str] = None
    impact_direction: Optional[str] = None
    impact_strength: Optional[str] = None
    affected_sectors: Optional[List[str]] = None
    action_suggestion: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None


# ============ 二级市场指标 ============

class MarketIndicatorFetchRequest(BaseModel):
    """二级市场指标采集请求"""
    types: Optional[List[str]] = Field(default=None, description="不传则采集全部，可选: advance_decline/limit_stats/volume/turnover/margin_trading/sector_ranking")


class MarketIndicatorHistoryQuery(BaseModel):
    """二级市场指标历史查询"""
    indicator_type: Optional[str] = Field(default=None, description="指标类型")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============ AI 洞察 ============

class InsightQuery(BaseModel):
    """洞察历史查询"""
    insight_type: Optional[str] = Field(default=None, description="类型: macro/industry/stock/event")
    ref_id: Optional[str] = Field(default=None, description="关联ID")
    limit: int = Field(default=10, ge=1, le=50)
