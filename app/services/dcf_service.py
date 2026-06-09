"""DCF 股票估值计算 - 核心计算服务

一比一复刻 stock_DCF/估值.ipynb 算法：
1. 解析价格CSV + 财务CSV
2. merge_asof 按日期合并
3. 计算6项财务指标
4. WACC + DCF 折现模型
5. 得出每股内在价值
"""

import io
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.schemas.dcf import (
    DCFModel,
    DCFResult,
    DCFValuationResponse,
    FinancialMetrics,
    WACCDetail,
    CSVValidationResponse,
    ValuateDirectRequest,
)

logger = logging.getLogger("webapi")

# ============================================================
# 常量：列名定义（与源 notebook 一一对应）
# ============================================================

# 16 项金融资产 + 长期股权投资（源码中金融资产=17项求和）
FINANCIAL_ASSET_COLUMNS = [
    "B_货币资金",
    "B_交易性金融资产",
    "B_衍生金融资产",
    "B_应收票据及应收账款",
    "B_应收票据",
    "B_应收账款",
    "B_应收款项融资",
    "B_应收利息",
    "B_应收股利",
    "B_其他应收款",
    "B_买入返售金融资产",
    "B_发放贷款及垫款",
    "B_可供出售金融资产",
    "B_持有至到期投资",
    "B_长期应收款",
    "B_长期股权投资",
    "B_投资性房地产",
]

# 9 项有息债务
DEBT_COLUMNS = [
    "B_短期借款",
    "B_交易性金融负债",
    "B_应付利息",
    "B_应付短期债券",
    "B_一年内到期的非流动负债",
    "B_长期借款",
    "B_应付债券",
    "B_租赁负债",
    "B_长期应付款(合计)",
]

# 合并所需的全部列
MERGE_COLUMNS = (
    FINANCIAL_ASSET_COLUMNS
    + ["B_所有者权益(或股东权益)合计"]
    + ["C_经营活动产生的现金流量净额"]
    + DEBT_COLUMNS
    + [
        "R_财务费用",
        "R_汇兑收益",
        "R_四、利润总额",
        "R_减：所得税费用",
        "C_固定资产折旧、油气资产折耗、生产性物资折旧",
        "C_无形资产摊销",
        "C_长期待摊费用摊销",
        "C_处置固定资产、无形资产和其他长期资产的损失",
        "B_少数股东权益",
    ]
)

# 价格 CSV 必需列
PRICE_REQUIRED_COLUMNS = ["股票代码", "股票名称", "交易日期", "总市值", "净利润TTM", "收盘价"]

# 财务 CSV 必需列（合并需要的核心列，含日期）
FINANCIAL_REQUIRED_COLUMNS = [
    "财报日期",
    "财报发布日期",
    "B_所有者权益(或股东权益)合计",
    "C_经营活动产生的现金流量净额",
    "R_财务费用",
    "R_汇兑收益",
    "R_四、利润总额",
    "R_减：所得税费用",
]


# ============================================================
# CSV 解析
# ============================================================


def parse_price_csv(content: bytes) -> pd.DataFrame:
    """解析价格 CSV（列：股票代码/股票名称/交易日期/总市值/净利润TTM/收盘价）

    源码读取方式: pd.read_csv(..., encoding='GBK', skiprows=1, parse_dates=['交易日期'])
    """
    # 尝试多种编码
    for encoding in ("utf-8", "gbk", "gb2312", "gb18030"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding, skiprows=1, parse_dates=["交易日期"])
            required = ["股票代码", "交易日期", "总市值", "净利润TTM", "收盘价"]
            if all(c in df.columns for c in required):
                cols = [c for c in PRICE_REQUIRED_COLUMNS if c in df.columns]
                df = df[cols]
                return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError("无法解析价格CSV文件，请检查编码和格式")


def parse_financial_csv(content: bytes) -> pd.DataFrame:
    """解析财务 CSV（~150列）

    源码读取方式:
    pd.read_csv(..., parse_dates=['财报日期', '财报发布日期'], skiprows=1, encoding='gbk')
    finance_df = finance_df.resample('Q', on='财报日期').first()
    """
    for encoding in ("utf-8", "gbk", "gb2312", "gb18030"):
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                encoding=encoding,
                skiprows=1,
                parse_dates=["财报日期", "财报发布日期"],
            )
            if "财报日期" in df.columns:
                # 源码：按季度重采样，取每季度第一条
                df = df.resample("QE", on="财报日期").first()
                df.reset_index(inplace=True)
                df.dropna(subset=["财报发布日期"], inplace=True)
                df.sort_values(by="财报发布日期", inplace=True)
                return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError("无法解析财务CSV文件，请检查编码和格式")


def merge_data(
    price_df: pd.DataFrame, finance_df: pd.DataFrame, stock_code: str, time: int
) -> pd.DataFrame:
    """merge_asof 按日期合并价格数据和财务数据

    源码：pd.merge_asof(df, finance_df[col], left_on='交易日期', right_on='财报日期', direction='backward')
    """
    # 筛选指定股票
    price_df = price_df[price_df["股票代码"] == stock_code].copy()
    price_df.sort_values(by="交易日期", inplace=True)

    # 确定财务数据中实际存在的列
    available_merge_cols = [c for c in MERGE_COLUMNS if c in finance_df.columns]
    select_cols = ["财报发布日期", "财报日期"] + available_merge_cols

    # merge_asof
    merged = pd.merge_asof(
        price_df,
        finance_df[select_cols],
        left_on="交易日期",
        right_on="财报日期",
        direction="backward",
    )

    if merged.empty:
        raise ValueError(f"合并后数据为空，请检查股票代码 '{stock_code}' 是否正确")

    return merged


def validate_csv(
    content: bytes, file_type: str, filename: str
) -> CSVValidationResponse:
    """校验 CSV 格式是否满足要求"""
    errors: List[str] = []
    columns: List[str] = []
    missing: List[str] = []

    try:
        # 尝试读取前几行获取列名
        for encoding in ("utf-8", "gbk", "gb2312"):
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=encoding, skiprows=1, nrows=2)
                columns = df.columns.tolist()
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        else:
            errors.append("无法解码CSV文件")
            return CSVValidationResponse(valid=False, file_type=file_type, errors=errors)

        # 全量读取获取行数
        try:
            full_df = pd.read_csv(io.BytesIO(content), encoding="gbk", skiprows=1)
            row_count = len(full_df)
        except Exception:
            try:
                full_df = pd.read_csv(io.BytesIO(content), encoding="utf-8", skiprows=1)
                row_count = len(full_df)
            except Exception:
                row_count = 0

        if file_type == "price":
            missing = [c for c in PRICE_REQUIRED_COLUMNS if c not in columns]
        elif file_type == "financial":
            missing = [c for c in FINANCIAL_REQUIRED_COLUMNS if c not in columns]
        else:
            errors.append(f"未知的文件类型: {file_type}")
            return CSVValidationResponse(
                valid=False, file_type=file_type, columns=columns, errors=errors
            )

        if missing:
            errors.append(f"缺失必需列: {', '.join(missing)}")

        return CSVValidationResponse(
            valid=len(errors) == 0,
            file_type=file_type,
            row_count=row_count,
            columns=columns,
            missing_columns=missing,
            errors=errors,
        )
    except Exception as e:
        errors.append(str(e))
        return CSVValidationResponse(
            valid=False, file_type=file_type, errors=errors
        )


# ============================================================
# 财务指标计算
# ============================================================


def calculate_financial_assets(row: pd.Series) -> float:
    """16项金融资产 + 长期股权投资 + 投资性房地产 求和（共17项）"""
    return sum(_safe_float(row.get(col, 0)) for col in FINANCIAL_ASSET_COLUMNS)


def calculate_company_debt(row: pd.Series) -> float:
    """9 项有息债务求和"""
    return sum(_safe_float(row.get(col, 0)) for col in DEBT_COLUMNS)


def calculate_operating_fcf(row: pd.Series) -> float:
    """经营资产自由现金流 = 经营活动现金流量净额 - 折旧 - 摊销 - 处置损失"""
    operating_cf = _safe_float(row.get("C_经营活动产生的现金流量净额", 0))
    depreciation = _safe_float(row.get("C_固定资产折旧、油气资产折耗、生产性物资折旧", 0))
    amortization_intangible = _safe_float(row.get("C_无形资产摊销", 0))
    amortization_longterm = _safe_float(row.get("C_长期待摊费用摊销", 0))
    disposal_loss = _safe_float(row.get("C_处置固定资产、无形资产和其他长期资产的损失", 0))
    return operating_cf - depreciation - amortization_intangible - amortization_longterm - disposal_loss


def calculate_effective_tax_rate(row: pd.Series) -> float:
    """实际企业所得税税率 = 1 - ((利润总额 - 所得税) / 利润总额)"""
    total_profit = _safe_float(row.get("R_四、利润总额", 0))
    income_tax = _safe_float(row.get("R_减：所得税费用", 0))
    if total_profit == 0:
        return 0.0
    return 1.0 - ((total_profit - income_tax) / total_profit)


def calculate_minority_interest_ratio(row: pd.Series) -> float:
    """少数股东权益比例 = 少数股东权益 / 股东权益合计"""
    minority = _safe_float(row.get("B_少数股东权益", 0))
    total_equity = _safe_float(row.get("B_所有者权益(或股东权益)合计", 0))
    if total_equity == 0:
        return 0.0
    return minority / total_equity


def calculate_debt_ratio(debt: float, equity: float) -> float:
    """债务占比 = 债务 / (股东权益 + 债务)"""
    total = equity + debt
    if total == 0:
        return 0.0
    return debt / total


def _safe_float(value) -> float:
    """安全转换为 float，处理 NaN/None"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


# ============================================================
# WACC 计算
# ============================================================


def calculate_wacc(now_df: pd.DataFrame, time: int, k_e: float = 0.09) -> Tuple[float, dict]:
    """计算加权平均资本成本 WACC

    源码:
    WACC = (债务资本成本总额 / ((公司债务 + 公司债务.shift(time)) / 2)
            * 债务占比 * (1-实际企业所得税税率))
            + (k_e * (1-债务占比))

    Returns: (wacc值, wacc明细dict)
    """
    # 债务资本成本率 = 债务资本总额 / 债务资本平均金额
    # 平均金额 = (当前债务 + time期前债务) / 2
    debt_avg = (now_df["公司债务"] + now_df["公司债务"].shift(time)) / 2
    cost_of_debt = now_df["债务资本成本总额"] / debt_avg
    cost_of_debt = cost_of_debt.fillna(0)

    # WACC = kd * D/(D+E) * (1-t) + ke * E/(D+E)
    wacc_series = (
        cost_of_debt * now_df["债务占比"] * (1 - now_df["实际企业所得税税率"])
        + k_e * (1 - now_df["债务占比"])
    )
    wacc = float(wacc_series.tolist()[-time])

    # 返回最近 time 期的明细
    idx = -time
    detail = {
        "wacc": wacc,
        "cost_of_debt": float(cost_of_debt.tolist()[idx]),
        "cost_of_equity": k_e,
        "debt_weight": float(now_df["债务占比"].tolist()[idx]),
        "equity_weight": 1.0 - float(now_df["债务占比"].tolist()[idx]),
        "tax_rate": float(now_df["实际企业所得税税率"].tolist()[idx]),
    }

    return wacc, detail


# ============================================================
# DCF 折现模型
# ============================================================


def dcf_zero_growth(fcf: float, wacc: float) -> Tuple[float, List[dict]]:
    """零增长模型: V = FCF / WACC"""
    fcf_pv = fcf / wacc
    return fcf_pv, []


def dcf_constant_growth(fcf: float, wacc: float, g: float) -> Tuple[float, List[dict]]:
    """不变增长模型: V = FCF(1+g) / (WACC-g)"""
    fcf_pv = fcf * (1 + g) / (wacc - g)
    return fcf_pv, [{"year": 1, "fcf": fcf * (1 + g), "growth_rate": g}]


def dcf_two_stage(
    fcf: float, wacc: float, g1: float, g2: float, t1_range: np.ndarray
) -> Tuple[float, List[dict]]:
    """两阶段模型

    源码:
        temp_sum = 0
        for _ in t1:
            temp = fcf * ((1+g1) ** _) / ((1+WACC) ** _)
            temp_sum = temp + temp_sum
        FCF = ((fcf * ((1+g1) ** (t1[-1]-1)) * (1+g2)) /
               ((WACC-g2)*((1+WACC)**t1[-1]))) + temp_sum
    """
    temp_sum = 0.0
    forecast = []

    for t in t1_range:
        temp = fcf * ((1 + g1) ** t) / ((1 + wacc) ** t)
        temp_sum += temp
        forecast.append({"year": int(t), "fcf": fcf * ((1 + g1) ** t), "growth_rate": g1})

    # 终值 = fcf * (1+g1)^(t1[-1]-1) * (1+g2) / ((WACC-g2) * (1+WACC)^t1[-1])
    # 注：源码中 t1[-1]-1 作为 fcf 增长指数，但实际上应该是 t1[-1]
    # 此处一比一复刻源码逻辑
    last_t = t1_range[-1]
    terminal_value = (
        fcf * ((1 + g1) ** (last_t - 1)) * (1 + g2)
        / ((wacc - g2) * ((1 + wacc) ** last_t))
    )

    # 终值年份的 FCF
    terminal_fcf = fcf * ((1 + g1) ** (last_t - 1)) * (1 + g2)
    forecast.append({"year": int(last_t) + 1, "fcf": terminal_fcf, "growth_rate": g2, "is_terminal": True})

    fcf_pv = temp_sum + terminal_value
    return fcf_pv, forecast


def dcf_three_stage(
    fcf: float, wacc: float, g1: float, g2: float, g3: float, t1_range: np.ndarray, t2_range: np.ndarray
) -> Tuple[float, List[dict]]:
    """三阶段模型

    源码:
        temp_sum1, temp_sum2 = 0, 0
        for _ in t1:
            temp1 = fcf * ((1+g1) ** _)
            temp = temp1 / ((1+WACC) ** _)
            temp_sum1 = temp + temp_sum1
        for _ in t2:
            temp = temp1 * ((1+g2) ** _) / ((1+WACC) ** (_+t1[-1]))
            temp_sum2 = temp + temp_sum2
        FCF = (temp1 * ((1+g2) ** t2) * (1+g3)) / ((WACC-g3)*((1+WACC)**(t1[-1]+t2[-1])))
              + temp_sum1 + temp_sum2
    """
    temp_sum1 = 0.0
    temp_sum2 = 0.0
    temp1 = 0.0
    forecast = []

    # 第一阶段
    for t in t1_range:
        temp1 = fcf * ((1 + g1) ** t)
        temp = temp1 / ((1 + wacc) ** t)
        temp_sum1 += temp
        forecast.append({"year": int(t), "fcf": temp1, "growth_rate": g1})

    # 第二阶段
    last_t1 = t1_range[-1]
    for t in t2_range:
        temp = temp1 * ((1 + g2) ** t) / ((1 + wacc) ** (t + last_t1))
        temp_sum2 += temp
        forecast.append({
            "year": int(t + last_t1),
            "fcf": temp1 * ((1 + g2) ** t),
            "growth_rate": g2,
        })

    # 终值
    last_t2 = t2_range[-1] if len(t2_range) > 0 else 1
    terminal_value = (
        temp1 * ((1 + g2) ** last_t2) * (1 + g3)
        / ((wacc - g3) * ((1 + wacc) ** (last_t1 + last_t2)))
    )
    terminal_fcf = temp1 * ((1 + g2) ** last_t2) * (1 + g3)
    forecast.append({
        "year": int(last_t1 + last_t2 + 1),
        "fcf": terminal_fcf,
        "growth_rate": g3,
        "is_terminal": True,
    })

    fcf_pv = terminal_value + temp_sum1 + temp_sum2
    return fcf_pv, forecast


# ============================================================
# 主入口：串联所有步骤
# ============================================================


def prepare_financial_data(merged_df: pd.DataFrame) -> pd.DataFrame:
    """数据预处理：计算各项财务指标

    源码 data_been_prepared() 函数的一比一复刻
    """
    now_df = pd.DataFrame()

    # 复制基础列
    base_cols = [c for c in ["股票代码", "股票名称", "交易日期", "总市值", "财报发布日期", "财报日期", "净利润TTM", "收盘价"] if c in merged_df.columns]
    now_df[base_cols] = merged_df[base_cols]

    # 金融资产（17项求和）
    now_df["金融资产"] = 0.0
    for col in FINANCIAL_ASSET_COLUMNS:
        if col in merged_df.columns:
            now_df["金融资产"] += merged_df[col].apply(_safe_float)

    # 公司债务（9项求和）
    now_df["公司债务"] = 0.0
    for col in DEBT_COLUMNS:
        if col in merged_df.columns:
            now_df["公司债务"] += merged_df[col].apply(_safe_float)

    # 债务资本成本总额
    fin_expense = _safe_float(0) if "R_财务费用" not in merged_df.columns else merged_df["R_财务费用"].apply(_safe_float)
    fx_gain = _safe_float(0) if "R_汇兑收益" not in merged_df.columns else merged_df["R_汇兑收益"].apply(_safe_float)
    now_df["债务资本成本总额"] = fin_expense + fx_gain

    # 经营资产自由现金流
    now_df["经营资产自由现金流"] = merged_df.apply(calculate_operating_fcf, axis=1)

    # 实际企业所得税税率
    now_df["实际企业所得税税率"] = merged_df.apply(calculate_effective_tax_rate, axis=1)

    # 少数股东权益比例
    now_df["少数股东权益比例"] = merged_df.apply(calculate_minority_interest_ratio, axis=1)

    # 债务占比
    now_df["债务占比"] = now_df.apply(
        lambda r: calculate_debt_ratio(r["公司债务"], _safe_float(merged_df.loc[r.name, "B_所有者权益(或股东权益)合计"]) if "B_所有者权益(或股东权益)合计" in merged_df.columns else 0),
        axis=1,
    )

    # 按财报日期去重（源码 drop_duplicates）
    if "财报日期" in now_df.columns:
        now_df.drop_duplicates(subset=["财报日期"], inplace=True)
    now_df.reset_index(drop=True, inplace=True)

    return now_df


def run_valuation(
    price_csv: bytes,
    financial_csv: bytes,
    stock_code: str,
    model: DCFModel,
    time: int = 4,
    g1: float = 0.2,
    g2: float = 0.03,
    g3: float = 0.01,
    t1_years: int = 2,
    t2_years: int = 1,
    k_e: float = 0.09,
) -> DCFValuationResponse:
    """DCF 估值主入口

    串联所有步骤：解析CSV -> 合并 -> 计算指标 -> WACC -> DCF折现 -> 每股价值
    """
    # 1. 解析 CSV
    price_df = parse_price_csv(price_csv)
    finance_df = parse_financial_csv(financial_csv)

    # 2. 合并数据
    merged_df = merge_data(price_df, finance_df, stock_code, time)

    # 3. 预处理财务数据
    now_df = prepare_financial_data(merged_df)

    if len(now_df) < time + 1:
        raise ValueError(f"数据不足：需要至少 {time + 1} 个季度数据，当前仅有 {len(now_df)} 个")

    # 4. 计算 WACC
    wacc, wacc_detail_dict = calculate_wacc(now_df, time, k_e)
    wacc_detail = WACCDetail(**wacc_detail_dict)

    # 5. 获取最近 time 期的指标
    idx = -time
    financial_assets = float(now_df["金融资产"].tolist()[idx])
    company_debt = float(now_df["公司债务"].tolist()[idx])
    operating_fcf = float(now_df["经营资产自由现金流"].tolist()[idx])
    tax_rate = float(now_df["实际企业所得税税率"].tolist()[idx])
    minority_ratio = float(now_df["少数股东权益比例"].tolist()[idx])
    debt_ratio_val = float(now_df["债务占比"].tolist()[idx])
    debt_cost = float(now_df["债务资本成本总额"].tolist()[idx])

    financial_metrics = FinancialMetrics(
        financial_assets=financial_assets,
        company_debt=company_debt,
        operating_fcf=operating_fcf,
        effective_tax_rate=tax_rate,
        minority_interest_ratio=minority_ratio,
        debt_ratio=debt_ratio_val,
        debt_capital_cost=debt_cost,
    )

    # 6. 选用 DCF 模型折现
    t1_range = np.arange(1, t1_years + 1)
    t2_range = np.arange(1, t2_years + 1)

    if model == DCFModel.ZERO_GROWTH:
        fcf_pv, forecast_fcf = dcf_zero_growth(operating_fcf, wacc)
    elif model == DCFModel.CONSTANT_GROWTH:
        fcf_pv, forecast_fcf = dcf_constant_growth(operating_fcf, wacc, g1)
    elif model == DCFModel.TWO_STAGE:
        fcf_pv, forecast_fcf = dcf_two_stage(operating_fcf, wacc, g1, g2, t1_range)
    elif model == DCFModel.THREE_STAGE:
        fcf_pv, forecast_fcf = dcf_three_stage(operating_fcf, wacc, g1, g2, g3, t1_range, t2_range)
    else:
        raise ValueError(f"不支持的模型: {model}")

    # 7. 计算每股内在价值（源码 fcf_discounted 函数）
    # 股权价值 = FCF折现值 + 金融资产 - 公司债务
    value = financial_assets - company_debt
    equity_value = (fcf_pv + value) * (1 - minority_ratio)

    # 股本 = 总市值 / 收盘价
    total_market_cap = float(now_df["总市值"].tolist()[idx])
    current_price = float(now_df["收盘价"].tolist()[idx])
    shares_outstanding = total_market_cap / current_price if current_price > 0 else 0

    intrinsic_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0

    # 安全边际
    safety_margin = None
    if current_price > 0:
        safety_margin = (intrinsic_value - current_price) / current_price * 100

    # 股票名称
    stock_name = None
    if "股票名称" in now_df.columns:
        names = now_df["股票名称"].dropna().tolist()
        if names:
            stock_name = str(names[-1])

    # 8. 历史价格序列（用于图表）
    price_history = []
    if "交易日期" in now_df.columns and "收盘价" in now_df.columns:
        for _, row in now_df.iterrows():
            date_val = row.get("交易日期")
            price_val = _safe_float(row.get("收盘价"))
            price_history.append({
                "date": str(date_val) if date_val and not pd.isna(date_val) else "",
                "price": price_val,
            })

    result = DCFResult(
        intrinsic_value_per_share=round(intrinsic_value, 4),
        total_equity_value=round(equity_value, 2),
        operating_fcf=round(operating_fcf, 2),
        fcf_present_value=round(fcf_pv, 2),
        financial_assets=round(financial_assets, 2),
        company_debt=round(company_debt, 2),
        net_asset_value=round(value, 2),
        minority_deduction=round(equity_value - (fcf_pv + value), 2),
        shares_outstanding=round(shares_outstanding, 0),
        current_price=round(current_price, 2),
        safety_margin=round(safety_margin, 2) if safety_margin is not None else None,
    )

    return DCFValuationResponse(
        stock_code=stock_code,
        stock_name=stock_name,
        model=model,
        wacc_detail=wacc_detail,
        financial_metrics=financial_metrics,
        result=result,
        parameters={
            "time": time,
            "g1": g1,
            "g2": g2,
            "g3": g3,
            "t1_years": t1_years,
            "t2_years": t2_years,
            "k_e": k_e,
        },
        forecast_fcf=forecast_fcf,
        price_history=price_history,
    )


def run_valuation_direct(req: ValuateDirectRequest) -> DCFValuationResponse:
    """直接估值入口：接收预计算的7项指标 + 价格数据，跳过CSV解析

    构造合成 DataFrame 供 calculate_wacc() 使用，后续复用 DCF 折现模型。
    """
    m = req.metrics
    time = req.time
    k_e = req.k_e

    # 构造合成 DataFrame：2 行相同值，供 calculate_wacc 使用
    # calculate_wacc 需要：公司债务, 债务资本成本总额, 债务占比, 实际企业所得税税率
    synth = pd.DataFrame({
        "公司债务": [m.company_debt, m.company_debt],
        "债务资本成本总额": [m.debt_capital_cost, m.debt_capital_cost],
        "债务占比": [m.debt_ratio, m.debt_ratio],
        "实际企业所得税税率": [m.effective_tax_rate, m.effective_tax_rate],
    })

    # WACC: 因为只有2行，time=4 会导致 shift(4) 全 NaN
    # 我们用 time=1 作为 WACC 计算的偏移量（实际使用最后1行）
    wacc_time = min(time, len(synth) - 1) if len(synth) > 1 else 1
    wacc, wacc_detail_dict = calculate_wacc(synth, wacc_time, k_e)
    wacc_detail = WACCDetail(**wacc_detail_dict)

    # DCF 折现
    operating_fcf = m.operating_fcf
    t1_range = np.arange(1, req.t1_years + 1)
    t2_range = np.arange(1, req.t2_years + 1)

    if req.model == DCFModel.ZERO_GROWTH:
        fcf_pv, forecast_fcf = dcf_zero_growth(operating_fcf, wacc)
    elif req.model == DCFModel.CONSTANT_GROWTH:
        fcf_pv, forecast_fcf = dcf_constant_growth(operating_fcf, wacc, req.g1)
    elif req.model == DCFModel.TWO_STAGE:
        fcf_pv, forecast_fcf = dcf_two_stage(operating_fcf, wacc, req.g1, req.g2, t1_range)
    elif req.model == DCFModel.THREE_STAGE:
        fcf_pv, forecast_fcf = dcf_three_stage(
            operating_fcf, wacc, req.g1, req.g2, req.g3, t1_range, t2_range
        )
    else:
        raise ValueError(f"不支持的模型: {req.model}")

    # 每股内在价值
    value = m.financial_assets - m.company_debt
    equity_value = (fcf_pv + value) * (1 - m.minority_interest_ratio)

    shares_outstanding = req.total_market_cap / req.current_price if req.current_price > 0 else 0
    intrinsic_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0

    safety_margin = None
    if req.current_price > 0:
        safety_margin = (intrinsic_value - req.current_price) / req.current_price * 100

    result = DCFResult(
        intrinsic_value_per_share=round(intrinsic_value, 4),
        total_equity_value=round(equity_value, 2),
        operating_fcf=round(operating_fcf, 2),
        fcf_present_value=round(fcf_pv, 2),
        financial_assets=round(m.financial_assets, 2),
        company_debt=round(m.company_debt, 2),
        net_asset_value=round(value, 2),
        minority_deduction=round(equity_value - (fcf_pv + value), 2),
        shares_outstanding=round(shares_outstanding, 0),
        current_price=round(req.current_price, 2),
        safety_margin=round(safety_margin, 2) if safety_margin is not None else None,
    )

    return DCFValuationResponse(
        stock_code=req.stock_code,
        stock_name=req.stock_name,
        model=req.model,
        wacc_detail=wacc_detail,
        financial_metrics=m,
        result=result,
        parameters={
            "time": time,
            "g1": req.g1,
            "g2": req.g2,
            "g3": req.g3,
            "t1_years": req.t1_years,
            "t2_years": req.t2_years,
            "k_e": req.k_e,
        },
        forecast_fcf=forecast_fcf,
        price_history=[],
    )
