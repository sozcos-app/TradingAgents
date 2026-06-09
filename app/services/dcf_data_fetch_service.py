"""DCF 自动获取财务数据 - AKShare 数据采集服务

通过 AKShare 获取资产负债表、利润表、现金流量表和历史行情，
映射为 DCF 模块所需的 B_/R_/C_ 列格式，并计算 7 项财务指标。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.schemas.dcf import (
    FetchFinancialDataResponse,
    FinancialMetrics,
    PeriodFinancialData,
    RawFinancialItem,
)
from app.services.dcf_service import (
    calculate_company_debt,
    calculate_debt_ratio,
    calculate_effective_tax_rate,
    calculate_financial_assets,
    calculate_minority_interest_ratio,
    calculate_operating_fcf,
    _safe_float,
)

logger = logging.getLogger("webapi")

# ============================================================
# AKShare 列名 → DCF 标准列名 映射
# AKShare 东方财富报表的中文列名去掉 B_/R_/C_ 前缀
# ============================================================

# 资产负债表映射: AKShare列名 → DCF B_ 前缀列名
AKSHARE_TO_DCF_BALANCE: Dict[str, str] = {
    "货币资金": "B_货币资金",
    "交易性金融资产": "B_交易性金融资产",
    "衍生金融资产": "B_衍生金融资产",
    "应收票据及应收账款": "B_应收票据及应收账款",
    "应收票据": "B_应收票据",
    "应收账款": "B_应收账款",
    "应收款项融资": "B_应收款项融资",
    "应收利息": "B_应收利息",
    "应收股利": "B_应收股利",
    "其他应收款": "B_其他应收款",
    "买入返售金融资产": "B_买入返售金融资产",
    "发放贷款及垫款": "B_发放贷款及垫款",
    "可供出售金融资产": "B_可供出售金融资产",
    "持有至到期投资": "B_持有至到期投资",
    "长期应收款": "B_长期应收款",
    "长期股权投资": "B_长期股权投资",
    "投资性房地产": "B_投资性房地产",
    "短期借款": "B_短期借款",
    "交易性金融负债": "B_交易性金融负债",
    "应付利息": "B_应付利息",
    "应付短期债券": "B_应付短期债券",
    "一年内到期的非流动负债": "B_一年内到期的非流动负债",
    "长期借款": "B_长期借款",
    "应付债券": "B_应付债券",
    "租赁负债": "B_租赁负债",
    "长期应付款(合计)": "B_长期应付款(合计)",
    "所有者权益(或股东权益)合计": "B_所有者权益(或股东权益)合计",
    "少数股东权益": "B_少数股东权益",
}

# 利润表映射（sina 接口列名与 DCF 的 R_ 前缀列名对应）
AKSHARE_TO_DCF_PROFIT: Dict[str, str] = {
    "财务费用": "R_财务费用",
    "汇兑收益": "R_汇兑收益",
    "利润总额": "R_四、利润总额",
    "所得税费用": "R_减：所得税费用",
}

# 现金流量表映射（sina 只有主表，折旧/摊销/处置损失等附注项目不在此列）
AKSHARE_TO_DCF_CASHFLOW: Dict[str, str] = {
    "经营活动产生的现金流量净额": "C_经营活动产生的现金流量净额",
}

# 所有映射合并
ALL_AKSHARE_MAPPINGS: Dict[str, str] = {
    **AKSHARE_TO_DCF_BALANCE,
    **AKSHARE_TO_DCF_PROFIT,
    **AKSHARE_TO_DCF_CASHFLOW,
}

# 科目分类（用于前端分组显示）
COLUMN_CATEGORIES: Dict[str, str] = {
    "B_货币资金": "balance_sheet",
    "B_交易性金融资产": "balance_sheet",
    "B_衍生金融资产": "balance_sheet",
    "B_应收票据及应收账款": "balance_sheet",
    "B_应收票据": "balance_sheet",
    "B_应收账款": "balance_sheet",
    "B_应收款项融资": "balance_sheet",
    "B_应收利息": "balance_sheet",
    "B_应收股利": "balance_sheet",
    "B_其他应收款": "balance_sheet",
    "B_买入返售金融资产": "balance_sheet",
    "B_发放贷款及垫款": "balance_sheet",
    "B_可供出售金融资产": "balance_sheet",
    "B_持有至到期投资": "balance_sheet",
    "B_长期应收款": "balance_sheet",
    "B_长期股权投资": "balance_sheet",
    "B_投资性房地产": "balance_sheet",
    "B_短期借款": "balance_sheet",
    "B_交易性金融负债": "balance_sheet",
    "B_应付利息": "balance_sheet",
    "B_应付短期债券": "balance_sheet",
    "B_一年内到期的非流动负债": "balance_sheet",
    "B_长期借款": "balance_sheet",
    "B_应付债券": "balance_sheet",
    "B_租赁负债": "balance_sheet",
    "B_长期应付款(合计)": "balance_sheet",
    "B_所有者权益(或股东权益)合计": "balance_sheet",
    "B_少数股东权益": "balance_sheet",
    "R_财务费用": "profit_sheet",
    "R_汇兑收益": "profit_sheet",
    "R_四、利润总额": "profit_sheet",
    "R_减：所得税费用": "profit_sheet",
    "C_经营活动产生的现金流量净额": "cash_flow",
    "C_固定资产折旧、油气资产折耗、生产性物资折旧": "cash_flow",
    "C_无形资产摊销": "cash_flow",
    "C_长期待摊费用摊销": "cash_flow",
    "C_处置固定资产、无形资产和其他长期资产的损失": "cash_flow",
}

# DCF 模块需要的所有目标列名
REQUIRED_DCF_COLUMNS = [
    "B_货币资金", "B_交易性金融资产", "B_衍生金融资产",
    "B_应收票据及应收账款", "B_应收票据", "B_应收账款",
    "B_应收款项融资", "B_应收利息", "B_应收股利",
    "B_其他应收款", "B_买入返售金融资产", "B_发放贷款及垫款",
    "B_可供出售金融资产", "B_持有至到期投资", "B_长期应收款",
    "B_长期股权投资", "B_投资性房地产",
    "B_短期借款", "B_交易性金融负债", "B_应付利息",
    "B_应付短期债券", "B_一年内到期的非流动负债",
    "B_长期借款", "B_应付债券", "B_租赁负债",
    "B_长期应付款(合计)", "B_所有者权益(或股东权益)合计",
    "B_少数股东权益",
    "R_财务费用", "R_汇兑收益", "R_四、利润总额", "R_减：所得税费用",
    "C_经营活动产生的现金流量净额",
    "C_固定资产折旧、油气资产折耗、生产性物资折旧",
    "C_无形资产摊销", "C_长期待摊费用摊销",
    "C_处置固定资产、无形资产和其他长期资产的损失",
]


def _extract_pure_code(stock_code: str) -> str:
    """从用户输入中提取纯数字代码: sz000977 -> 000977"""
    code = stock_code.strip().lower()
    for prefix in ("sz", "sh", "bj"):
        if code.startswith(prefix):
            code = code[len(prefix):]
            break
    return code


def _reverse_mapping() -> Dict[str, str]:
    """生成 DCF列名 → AKShare列名 的反向映射"""
    return {v: k for k, v in ALL_AKSHARE_MAPPINGS.items()}


def _compute_metrics_from_row(row: pd.Series) -> FinancialMetrics:
    """从一行已映射的数据中计算7项指标"""
    financial_assets = calculate_financial_assets(row)
    company_debt = calculate_company_debt(row)
    operating_fcf = calculate_operating_fcf(row)
    effective_tax_rate = calculate_effective_tax_rate(row)
    minority_ratio = calculate_minority_interest_ratio(row)
    equity = _safe_float(row.get("B_所有者权益(或股东权益)合计", 0))
    debt_ratio = calculate_debt_ratio(company_debt, equity)
    fin_expense = _safe_float(row.get("R_财务费用", 0))
    fx_gain = _safe_float(row.get("R_汇兑收益", 0))
    debt_cost = fin_expense + fx_gain

    return FinancialMetrics(
        financial_assets=financial_assets,
        company_debt=company_debt,
        operating_fcf=operating_fcf,
        effective_tax_rate=effective_tax_rate,
        minority_interest_ratio=minority_ratio,
        debt_ratio=debt_ratio,
        debt_capital_cost=debt_cost,
    )


class DcfDataFetchService:
    """AKShare 财务数据采集服务"""

    @staticmethod
    async def fetch_financial_data(
        stock_code: str, quarters: int = 8
    ) -> FetchFinancialDataResponse:
        """获取多期财务数据

        使用 stock_financial_report_sina 接口（stock_balance_sheet_by_report_em 已失效）。
        数据格式：行=报告期，列=科目名，日期列=报告日。

        Args:
            stock_code: 股票代码，如 sz000977
            quarters: 获取最近多少个报告期
        """
        pure_code = _extract_pure_code(stock_code)
        try:
            import akshare as ak
        except ImportError:
            raise RuntimeError("akshare 未安装，请执行 pip install akshare")

        columns_found: List[str] = []
        columns_missing: List[str] = []

        # 1. 并行获取三张报表（使用 sina 接口）
        async def _fetch_report(symbol_name: str):
            return await asyncio.to_thread(
                lambda: ak.stock_financial_report_sina(stock=pure_code, symbol=symbol_name)
            )

        balance_df, profit_df, cashflow_df = await asyncio.gather(
            _fetch_report("资产负债表"),
            _fetch_report("利润表"),
            _fetch_report("现金流量表"),
            return_exceptions=True,
        )

        if isinstance(balance_df, Exception):
            logger.error(f"资产负债表获取失败: {balance_df}")
            balance_df = pd.DataFrame()
        if isinstance(profit_df, Exception):
            logger.error(f"利润表获取失败: {profit_df}")
            profit_df = pd.DataFrame()
        if isinstance(cashflow_df, Exception):
            logger.error(f"现金流量表获取失败: {cashflow_df}")
            cashflow_df = pd.DataFrame()

        if balance_df.empty and profit_df.empty and cashflow_df.empty:
            raise ValueError(f"未能获取到 {pure_code} 的财务数据，请检查股票代码是否正确")

        # 2. 列名映射：sina 中文列名 → DCF B_/R_/C_ 列名
        def _rename_df(df: pd.DataFrame) -> pd.DataFrame:
            rename_map = {}
            for col in df.columns:
                if col in ALL_AKSHARE_MAPPINGS:
                    rename_map[col] = ALL_AKSHARE_MAPPINGS[col]
            found = set(rename_map.values())
            return df.rename(columns=rename_map), found

        balance_df, balance_found = _rename_df(balance_df)
        profit_df, profit_found = _rename_df(profit_df)
        cashflow_df, cf_found = _rename_df(cashflow_df)
        columns_found = list(balance_found | profit_found | cf_found)
        columns_missing = [c for c in REQUIRED_DCF_COLUMNS if c not in columns_found]

        # 3. 按报告日合并三张报表
        # sina 接口返回格式：行=报告期，列=科目，日期列="报告日"（格式 YYYYMMDD）
        date_col = "报告日"
        renamed_date = "report_date"

        def _prepare(df: pd.DataFrame) -> pd.DataFrame:
            """提取日期列 + DCF 映射后的列，按报告期去重"""
            if df.empty or date_col not in df.columns:
                return pd.DataFrame()
            dcf_cols = [c for c in df.columns if c in REQUIRED_DCF_COLUMNS]
            if not dcf_cols:
                return pd.DataFrame()
            sub = df[[date_col] + dcf_cols].copy()
            sub.rename(columns={date_col: renamed_date}, inplace=True)
            sub[renamed_date] = sub[renamed_date].astype(str)
            sub = sub.drop_duplicates(subset=[renamed_date], keep="first")
            return sub

        bal_sub = _prepare(balance_df)
        prof_sub = _prepare(profit_df)
        cf_sub = _prepare(cashflow_df)

        if bal_sub.empty and prof_sub.empty and cf_sub.empty:
            raise ValueError(f"未能映射到 {pure_code} 的任何 DCF 列，请检查列名映射")

        # 合并：以资产负债表为主表，左连接利润表和现金流量表
        from functools import reduce
        parts = [df for df in (bal_sub, prof_sub, cf_sub) if not df.empty]
        if len(parts) == 1:
            merged = parts[0]
        else:
            merged = reduce(
                lambda left, right: pd.merge(left, right, on=renamed_date, how="outer"),
                parts,
            )

        # 填充 NaN 为 0
        for col in REQUIRED_DCF_COLUMNS:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0)

        # 4. 取最近 quarters 期
        merged[renamed_date] = pd.to_datetime(merged[renamed_date], format="%Y%m%d", errors="coerce")
        merged = merged.dropna(subset=[renamed_date])
        merged = merged.sort_values(renamed_date, ascending=False).head(quarters)

        # 5. 获取股价和市值数据
        total_market_cap: Optional[float] = None
        current_price: Optional[float] = None
        shares_outstanding: Optional[float] = None
        stock_name: Optional[str] = None

        # 个股信息（名称 + 市值 + 最新价）
        try:
            info_result = await asyncio.to_thread(
                lambda: ak.stock_individual_info_em(symbol=pure_code)
            )
            if isinstance(info_result, pd.DataFrame) and not info_result.empty:
                info_dict = dict(zip(info_result["item"], info_result["value"]))
                stock_name = str(info_dict.get("股票简称", ""))
                total_market_cap = _safe_float(info_dict.get("总市值"))
                current_price = _safe_float(info_dict.get("最新"))
                logger.info(f"个股信息获取成功: name={stock_name}, cap={total_market_cap}, price={current_price}")
        except Exception as e:
            logger.warning(f"个股信息获取失败: {e}")

        # 实时行情兜底（用 em 接口 stock_zh_a_spot_em，包含总市值和最新价列）
        if total_market_cap is None or current_price is None:
            try:
                spot_result = await asyncio.to_thread(lambda: ak.stock_zh_a_spot_em())
                if isinstance(spot_result, pd.DataFrame) and not spot_result.empty:
                    if "代码" in spot_result.columns:
                        row = spot_result[spot_result["代码"] == pure_code]
                        if not row.empty:
                            latest = row.iloc[0]
                            if current_price is None and "最新价" in latest.index:
                                current_price = _safe_float(latest.get("最新价", 0))
                            if total_market_cap is None and "总市值" in latest.index:
                                total_market_cap = _safe_float(latest.get("总市值", 0))
                            logger.info(f"东货行情兜底: price={current_price}, cap={total_market_cap}")
            except Exception as e:
                logger.warning(f"实时行情(东财)获取失败: {e}")

        # 历史行情兜底（仅取最近1天收盘价）
        if current_price is None:
            try:
                import datetime
                end_date = datetime.date.today().strftime("%Y%m%d")
                start_date = (datetime.date.today() - datetime.timedelta(days=10)).strftime("%Y%m%d")
                hist_df = await asyncio.to_thread(
                    lambda: ak.stock_zh_a_hist(
                        symbol=pure_code, period="daily",
                        start_date=start_date, end_date=end_date, adjust="qfq"
                    )
                )
                if isinstance(hist_df, pd.DataFrame) and not hist_df.empty:
                    current_price = _safe_float(hist_df.iloc[-1]["收盘"])
                    logger.info(f"历史行情兜底获取收盘价: {current_price}")
            except Exception as e:
                logger.warning(f"历史行情兜底失败: {e}")

        # 从资产负债表取"实收资本(或股本)"作为总股本，再算市值
        if shares_outstanding is None and not balance_df.empty:
            cap_col = "实收资本(或股本)" if "实收资本(或股本)" in balance_df.columns else None
            if cap_col:
                latest_cap = balance_df[cap_col].iloc[0]
                shares_outstanding = _safe_float(latest_cap)
                if shares_outstanding and shares_outstanding > 0 and current_price:
                    total_market_cap = shares_outstanding * current_price
                logger.info(f"从资产负债表取总股本: {shares_outstanding}, 算出市值: {total_market_cap}")

        if total_market_cap is None and current_price and current_price > 0 and shares_outstanding:
            total_market_cap = shares_outstanding * current_price

        logger.info(
            f"最终数据汇总: stock={stock_code}, name={stock_name}, "
            f"price={current_price}, market_cap={total_market_cap}, shares={shares_outstanding}"
        )

        # 6. 构建每期数据
        periods: List[PeriodFinancialData] = []
        for _, row in merged.iterrows():
            report_date = str(row.get(renamed_date, ""))[:10]
            raw_items: List[RawFinancialItem] = []
            for col in REQUIRED_DCF_COLUMNS:
                if col in row.index:
                    cat = COLUMN_CATEGORIES.get(col, "balance_sheet")
                    raw_items.append(
                        RawFinancialItem(
                            dcf_column=col,
                            display_name=col,
                            value=_safe_float(row.get(col, 0)),
                            category=cat,
                        )
                    )
            metrics = _compute_metrics_from_row(row)
            periods.append(
                PeriodFinancialData(
                    report_date=report_date,
                    raw_items=raw_items,
                    metrics=metrics,
                )
            )

        return FetchFinancialDataResponse(
            stock_code=stock_code,
            stock_name=stock_name,
            total_market_cap=total_market_cap,
            current_price=current_price,
            shares_outstanding=shares_outstanding,
            periods=periods,
            columns_found=columns_found,
            columns_missing=columns_missing,
        )
