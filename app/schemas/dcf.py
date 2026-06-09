"""DCF 股票估值计算 - 请求/响应 Pydantic 模型"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DCFModel(str, Enum):
    """DCF 折现模型类型"""
    ZERO_GROWTH = "zero-growth"
    CONSTANT_GROWTH = "constant-growth"
    TWO_STAGE = "two-stage"
    THREE_STAGE = "three-stage"


class FinancialMetrics(BaseModel):
    """财务指标"""
    financial_assets: float = Field(description="金融资产合计")
    company_debt: float = Field(description="公司债务合计")
    operating_fcf: float = Field(description="经营资产自由现金流")
    effective_tax_rate: float = Field(description="实际企业所得税税率")
    minority_interest_ratio: float = Field(description="少数股东权益比例")
    debt_ratio: float = Field(description="债务占比")
    debt_capital_cost: float = Field(description="债务资本成本总额")


class WACCDetail(BaseModel):
    """WACC 计算明细"""
    wacc: float = Field(description="加权平均资本成本")
    cost_of_debt: float = Field(description="债务资本成本率")
    cost_of_equity: float = Field(description="股权资本成本率(默认9%)")
    debt_weight: float = Field(description="债务权重 D/(D+E)")
    equity_weight: float = Field(description="股权权重 E/(D+E)")
    tax_rate: float = Field(description="实际所得税税率")


class DCFResult(BaseModel):
    """DCF 估值结果"""
    intrinsic_value_per_share: float = Field(description="每股内在价值")
    total_equity_value: float = Field(description="归属于上市公司股东的价值")
    operating_fcf: float = Field(description="经营资产自由现金流")
    fcf_present_value: float = Field(description="FCF 折现值")
    financial_assets: float = Field(description="金融资产")
    company_debt: float = Field(description="公司债务")
    net_asset_value: float = Field(description="净金融资产(金融资产-债务)")
    minority_deduction: float = Field(description="少数股东扣减金额")
    shares_outstanding: float = Field(description="总股本(股)")
    current_price: Optional[float] = Field(default=None, description="当前股价")
    safety_margin: Optional[float] = Field(default=None, description="安全边际(%)")


class DCFValuationResponse(BaseModel):
    """DCF 估值完整响应"""
    stock_code: str = Field(description="股票代码")
    stock_name: Optional[str] = Field(default=None, description="股票名称")
    model: DCFModel = Field(description="使用的DCF模型")
    wacc_detail: WACCDetail = Field(description="WACC计算明细")
    financial_metrics: FinancialMetrics = Field(description="财务指标")
    result: DCFResult = Field(description="估值结果")
    parameters: dict = Field(description="使用的参数")
    forecast_fcf: List[dict] = Field(default_factory=list, description="预测FCF序列(用于图表)")
    price_history: List[dict] = Field(default_factory=list, description="历史价格序列(用于图表)")


class CSVValidationResponse(BaseModel):
    """CSV 校验响应"""
    valid: bool = Field(description="是否有效")
    file_type: str = Field(description="文件类型: price/financial")
    row_count: int = Field(default=0, description="数据行数")
    columns: List[str] = Field(default_factory=list, description="CSV包含的列名")
    missing_columns: List[str] = Field(default_factory=list, description="缺失的必需列")
    errors: List[str] = Field(default_factory=list, description="校验错误信息")


class CninfoAnnouncement(BaseModel):
    """巨潮资讯公告记录"""
    title: str = Field(description="公告标题")
    announcement_id: str = Field(default="", description="公告ID")
    announcement_type: Optional[str] = Field(default="", description="公告类型")
    stock_code: str = Field(default="", description="股票代码")
    sec_name: str = Field(default="", description="股票名称")
    sec_code: str = Field(default="", description="证券代码")
    pub_date: str = Field(default="", description="发布日期(YYYY-MM-DD)")
    adjunct_url: str = Field(default="", description="附件URL路径")
    adjunct_size: int = Field(default=0, description="附件大小(bytes)")
    download_url: str = Field(default="", description="完整下载URL")


class CninfoSearchResponse(BaseModel):
    """巨潮资讯搜索结果"""
    total: int = Field(default=0, description="总记录数")
    announcements: List[CninfoAnnouncement] = Field(default_factory=list, description="公告列表")


class RawFinancialItem(BaseModel):
    """单条原始财务科目"""
    dcf_column: str = Field(description="DCF标准列名(如 B_货币资金)")
    display_name: str = Field(description="显示名称")
    value: float = Field(default=0, description="金额")
    category: str = Field(description="分类: balance_sheet / profit_sheet / cash_flow")


class PeriodFinancialData(BaseModel):
    """单期财务数据"""
    report_date: str = Field(description="报告期")
    raw_items: List[RawFinancialItem] = Field(default_factory=list, description="原始科目列表")
    metrics: Optional[FinancialMetrics] = Field(default=None, description="计算后的7项指标")


class FetchFinancialDataResponse(BaseModel):
    """自动获取财务数据响应"""
    stock_code: str = Field(description="股票代码")
    stock_name: Optional[str] = Field(default=None, description="股票名称")
    total_market_cap: Optional[float] = Field(default=None, description="总市值(元)")
    current_price: Optional[float] = Field(default=None, description="当前股价")
    shares_outstanding: Optional[float] = Field(default=None, description="总股本(股)")
    periods: List[PeriodFinancialData] = Field(default_factory=list, description="多期财务数据")
    columns_found: List[str] = Field(default_factory=list, description="成功映射的列")
    columns_missing: List[str] = Field(default_factory=list, description="未找到的列")


class ValuateDirectRequest(BaseModel):
    """直接估值请求（跳过CSV）"""
    stock_code: str = Field(description="股票代码")
    stock_name: Optional[str] = Field(default=None, description="股票名称")
    model: DCFModel = Field(description="DCF模型")
    time: int = Field(default=4, description="采用最近n期的数据(季度)")
    g1: float = Field(default=0.2, description="第一阶段增长率")
    g2: float = Field(default=0.03, description="第二阶段增长率")
    g3: float = Field(default=0.01, description="第三阶段增长率")
    t1_years: int = Field(default=2, description="第一阶段年数")
    t2_years: int = Field(default=1, description="第二阶段年数")
    k_e: float = Field(default=0.09, description="股权资本成本率")
    metrics: FinancialMetrics = Field(description="7项财务指标")
    total_market_cap: float = Field(description="总市值(元)")
    current_price: float = Field(description="当前股价(元)")
