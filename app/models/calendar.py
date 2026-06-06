"""
交易日历 - 数据模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Annotated
from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer, ConfigDict
from bson import ObjectId


def validate_object_id(v: Any) -> ObjectId:
    """验证 ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return ObjectId(v)
    raise ValueError("Invalid ObjectId")


def serialize_object_id(v: ObjectId) -> str:
    """序列化 ObjectId 为字符串"""
    return str(v)


PyObjectId = Annotated[
    ObjectId,
    BeforeValidator(validate_object_id),
    PlainSerializer(serialize_object_id, return_type=str),
]


class MacroIndicator(BaseModel):
    """宏观指标"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    indicator_name: str = Field(..., description="指标名称，如 PMI、CPI、社融同比")
    value: float = Field(..., description="指标值")
    unit: str = Field(default="%", description="单位")
    date: datetime = Field(..., description="数据日期")
    source: str = Field(default="", description="数据来源")
    year_on_year: Optional[float] = Field(default=None, description="同比变化")
    month_on_month: Optional[float] = Field(default=None, description="环比变化")
    score: Optional[int] = Field(default=None, description="单项评分 0~100")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class MacroScore(BaseModel):
    """宏观评分"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    total_score: float = Field(..., description="总分 0~100")
    level: str = Field(..., description="可积极参与/谨慎试仓/防守观望")
    details: Dict[str, Any] = Field(default_factory=dict, description="各指标得分明细")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="预警列表")
    date: datetime = Field(default_factory=datetime.utcnow, description="评分日期")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class IndustryProsperity(BaseModel):
    """行业景气"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    industry_name: str = Field(..., description="行业名称")
    inventory_cycle: str = Field(default="", description="库存周期阶段")
    inventory_score: float = Field(default=0, description="库存周期得分 0~30")
    profit_trend: str = Field(default="", description="盈利趋势")
    profit_score: float = Field(default=0, description="盈利趋势得分 0~20")
    demand_growth: str = Field(default="", description="需求增速")
    demand_score: float = Field(default=0, description="需求增速得分 0~20")
    capital_flow: str = Field(default="", description="资金流向")
    capital_score: float = Field(default=0, description="资金流向得分 0~15")
    policy_support: str = Field(default="", description="政策支持")
    policy_score: float = Field(default=0, description="政策支持得分 0~15")
    score: float = Field(default=0, description="景气评分 0~100")
    suggestion: str = Field(default="标配", description="超配/标配/低配")
    catalysts: List[str] = Field(default_factory=list, description="核心催化剂")
    date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class StockHealthCheck(BaseModel):
    """个股体检"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    ts_code: str = Field(..., description="股票代码")
    stock_name: str = Field(default="", description="股票名称")
    main_business_score: float = Field(default=0, description="主营匹配度 0~30")
    main_business_detail: Dict[str, Any] = Field(default_factory=dict)
    profit_quality_score: float = Field(default=0, description="利润含金量 0~25")
    profit_quality_detail: Dict[str, Any] = Field(default_factory=dict)
    gross_margin_score: float = Field(default=0, description="毛利率合理性 0~20")
    gross_margin_detail: Dict[str, Any] = Field(default_factory=dict)
    disclosure_score: float = Field(default=0, description="信披记录 0~15")
    disclosure_detail: Dict[str, Any] = Field(default_factory=dict)
    supply_chain_score: float = Field(default=0, description="供应链验证 0~10")
    supply_chain_detail: Dict[str, Any] = Field(default_factory=dict)
    deduction: float = Field(default=0, description="扣分(解禁/减持)")
    total_score: float = Field(default=0, description="总分 0~100")
    risk_level: str = Field(default="中", description="低/中/高")
    conclusion: str = Field(default="谨慎", description="可关注/谨慎/回避")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="预警项")
    date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class MarketEvent(BaseModel):
    """市场事件"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str = Field(..., description="事件标题")
    event_type: str = Field(..., description="事件类型")
    event_date: datetime = Field(..., description="事件日期")
    impact_direction: str = Field(default="中性", description="利多/利空/中性")
    impact_strength: str = Field(default="低", description="高/中/低")
    affected_sectors: List[str] = Field(default_factory=list, description="影响板块")
    action_suggestion: str = Field(default="", description="行动建议")
    source: str = Field(default="", description="信息来源")
    description: str = Field(default="", description="事件描述")
    is_auto: bool = Field(default=False, description="是否自动采集")
    created_by: str = Field(default="system", description="创建人")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


# 事件类型字典
EVENT_TYPES = [
    ("财报", "财报披露"),
    ("政策", "政策变更"),
    ("解禁", "限售股解禁"),
    ("地缘", "地缘政治"),
    ("指数调整", "指数调整"),
    ("宏观数据", "宏观数据发布"),
    ("龙头事件", "龙头企业事件"),
    ("机构考核", "机构调仓考核"),
    ("交易制度", "交易制度变更"),
    ("其他", "其他"),
]


class MarketIndicator(BaseModel):
    """二级市场指标"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    indicator_type: str = Field(..., description="指标类型: advance_decline/limit_stats/volume/turnover/margin_trading/sector_ranking")
    date: datetime = Field(default_factory=datetime.utcnow, description="数据日期")
    source: str = Field(default="", description="数据来源")
    # 涨跌家数
    up_count: Optional[int] = Field(default=None, description="上涨家数")
    down_count: Optional[int] = Field(default=None, description="下跌家数")
    flat_count: Optional[int] = Field(default=None, description="平盘家数")
    # 涨停跌停
    limit_up_count: Optional[int] = Field(default=None, description="涨停数")
    limit_down_count: Optional[int] = Field(default=None, description="跌停数")
    # 成交额
    total_amount: Optional[float] = Field(default=None, description="全市场成交额(元)")
    # 换手率
    avg_turnover_rate: Optional[float] = Field(default=None, description="全市场平均换手率")
    # 融资融券
    margin_buy: Optional[float] = Field(default=None, description="融资买入额(元)")
    margin_balance: Optional[float] = Field(default=None, description="融资余额(元)")
    short_balance: Optional[float] = Field(default=None, description="融券余额(元)")
    # 板块
    sector_name: Optional[str] = Field(default=None, description="板块名称")
    change_pct: Optional[float] = Field(default=None, description="板块涨跌幅%")
    turnover_rate: Optional[float] = Field(default=None, description="板块换手率")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class DivergenceSignal(BaseModel):
    """背离信号"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    judgment: str = Field(default="", description="综合判断: 谎言风险/潜在机会/信号矛盾/无明显背离")
    description: str = Field(default="", description="判断描述")
    action: str = Field(default="", description="行动建议")
    signals: List[Dict[str, Any]] = Field(default_factory=list, description="信号详情")
    lie_count: int = Field(default=0, description="谎言信号数")
    opportunity_count: int = Field(default=0, description="机会信号数")
    macro_score: Optional[float] = Field(default=None, description="关联的宏观评分")
    date: datetime = Field(default_factory=datetime.utcnow, description="检测日期")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
