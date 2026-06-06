"""
行业景气评分引擎
五维度评分：库存周期(30) + 盈利趋势(20) + 需求增速(20) + 资金流向(15) + 政策支持(15)
总分 0~100，输出超配/标配/低配
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("industry_score_engine")


class IndustryScoreEngine:
    """行业评分引擎"""

    WEIGHTS = {
        "库存周期": 30,
        "盈利趋势": 20,
        "需求增速": 20,
        "资金流向": 15,
        "政策支持": 15,
    }

    def score_inventory_cycle(self, inventory_yoy: float = None, ppi_yoy: float = None) -> Dict[str, Any]:
        """库存周期评分（0~30）"""
        if inventory_yoy is None or ppi_yoy is None:
            return {"score": 15, "max": 30, "phase": "数据不足", "detail": "缺少库存或PPI数据"}

        inv_down = inventory_yoy < 0
        ppi_up = ppi_yoy > 0

        if not inv_down and ppi_up:
            # 被动去库：库存降 + 价格升 → 景气即将上行
            return {"score": 30, "max": 30, "phase": "被动去库", "detail": "库存下降+价格回升，景气即将上行"}
        elif not inv_down and not ppi_up:
            # 主动去库：库存降 + 价格降 → 景气低谷
            return {"score": 10, "max": 30, "phase": "主动去库", "detail": "库存下降+价格下降，景气低谷"}
        elif inv_down and ppi_up:
            # 主动补库：库存增 + 价格升 → 景气高峰
            return {"score": 25, "max": 30, "phase": "主动补库", "detail": "库存上升+价格回升，景气高峰"}
        else:
            # 被动补库：库存增 + 价格降 → 景气下行
            return {"score": 15, "max": 30, "phase": "被动补库", "detail": "库存上升+价格下降，景气下行"}

    def score_profitability(self, roe: float = None, margin: float = None, trend: str = "unknown") -> Dict[str, Any]:
        """盈利趋势评分（0~20）"""
        if roe is None:
            return {"score": 10, "max": 20, "detail": "缺少ROE数据"}

        score = 10  # 基础分

        # ROE 水平
        if roe > 15:
            score += 5
        elif roe > 10:
            score += 3
        elif roe > 5:
            score += 1

        # 趋势
        if trend == "up":
            score += 5
        elif trend == "down":
            score -= 3

        score = max(0, min(20, score))
        return {"score": score, "max": 20, "roe": roe, "margin": margin, "detail": f"ROE={roe}%, 趋势={trend}"}

    def score_demand(self, sales_yoy: float = None) -> Dict[str, Any]:
        """需求增速评分（0~20）"""
        if sales_yoy is None:
            return {"score": 10, "max": 20, "detail": "缺少需求数据"}

        if sales_yoy > 20:
            return {"score": 20, "max": 20, "detail": f"需求旺盛，同比增长{sales_yoy}%"}
        elif sales_yoy > 10:
            return {"score": 15, "max": 20, "detail": f"需求增长，同比增长{sales_yoy}%"}
        elif sales_yoy > 0:
            return {"score": 10, "max": 20, "detail": f"需求平稳，同比增长{sales_yoy}%"}
        else:
            return {"score": 3, "max": 20, "detail": f"需求萎缩，同比{sales_yoy}%"}

    def score_capital_flow(self, net_pct: float = None, turnover_rate: float = None, up_ratio: float = None) -> Dict[str, Any]:
        """资金流向评分（0~15）"""
        score = 8  # 基础分

        if net_pct is not None:
            if net_pct > 5:
                score += 5
            elif net_pct > 0:
                score += 3
            elif net_pct < -5:
                score -= 5
            else:
                score -= 2

        if turnover_rate is not None:
            if turnover_rate > 5:
                score += 2
            elif turnover_rate > 2:
                score += 1

        score = max(0, min(15, score))
        return {"score": score, "max": 15, "net_pct": net_pct, "detail": f"主力净占比={net_pct}%"}

    def score_policy(self, policy_count: int = 0, policy_level: str = "unknown") -> Dict[str, Any]:
        """政策支持评分（0~15）"""
        score = 5  # 基础分

        if policy_level == "national":
            score += 8
        elif policy_level == "provincial":
            score += 4

        if policy_count > 3:
            score += 2

        score = max(0, min(15, score))
        return {"score": score, "max": 15, "detail": f"政策数量={policy_count}, 级别={policy_level}"}

    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算行业景气总分
        data: { inventory_yoy, ppi_yoy, roe, margin, trend, sales_yoy, net_pct, turnover_rate, policy_count, policy_level }
        """
        inv = self.score_inventory_cycle(data.get("inventory_yoy"), data.get("ppi_yoy"))
        profit = self.score_profitability(data.get("roe"), data.get("margin"), data.get("trend", "unknown"))
        demand = self.score_demand(data.get("sales_yoy"))
        capital = self.score_capital_flow(data.get("net_pct"), data.get("turnover_rate"))
        policy = self.score_policy(data.get("policy_count", 0), data.get("policy_level", "unknown"))

        total = inv["score"] + profit["score"] + demand["score"] + capital["score"] + policy["score"]

        if total >= 70:
            suggestion = "超配"
        elif total >= 50:
            suggestion = "标配"
        else:
            suggestion = "低配"

        return {
            "score": total,
            "suggestion": suggestion,
            "details": {
                "库存周期": inv,
                "盈利趋势": profit,
                "需求增速": demand,
                "资金流向": capital,
                "政策支持": policy,
            },
        }

    def quick_score_from_market(self, sector_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于市场数据的快速评分（简化版，不需要完整五维度数据）
        仅用成交额排名、涨跌幅、资金流向做粗略评分
        """
        score = 50  # 基础分

        # 涨跌幅
        change_pct = sector_data.get("change_pct", 0)
        if change_pct > 3:
            score += 15
        elif change_pct > 1:
            score += 8
        elif change_pct < -3:
            score -= 15
        elif change_pct < -1:
            score -= 8

        # 换手率
        turnover = sector_data.get("turnover_rate", 0)
        if turnover > 5:
            score += 10
        elif turnover > 2:
            score += 5

        # 涨跌比
        up_count = sector_data.get("up_count", 0)
        down_count = sector_data.get("down_count", 0)
        total = up_count + down_count
        if total > 0:
            up_ratio = up_count / total
            if up_ratio > 0.7:
                score += 10
            elif up_ratio > 0.5:
                score += 5
            elif up_ratio < 0.3:
                score -= 10

        score = max(0, min(100, score))

        if score >= 70:
            suggestion = "超配"
        elif score >= 50:
            suggestion = "标配"
        else:
            suggestion = "低配"

        return {
            "score": score,
            "suggestion": suggestion,
            "inventory_cycle": "-",
            "inventory_score": 0,
            "profit_trend": "-",
            "profit_score": 0,
            "demand_growth": "-",
            "demand_score": 0,
            "capital_flow": f"涨跌{change_pct}%",
            "capital_score": 0,
            "policy_support": "-",
            "policy_score": 0,
            "catalysts": [],
            "is_quick": True,
        }

    def full_score_with_details(self, dimension_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于五维度完整数据的评分
        dimension_data: { inventory_yoy, ppi_yoy, roe, margin, trend, sales_yoy,
                          net_pct, turnover_rate, policy_count, policy_level, ... }
        """
        inv = self.score_inventory_cycle(dimension_data.get("inventory_yoy"), dimension_data.get("ppi_yoy"))
        profit = self.score_profitability(dimension_data.get("roe"), dimension_data.get("margin"), dimension_data.get("trend", "unknown"))
        demand = self.score_demand(dimension_data.get("sales_yoy"))
        capital = self.score_capital_flow(dimension_data.get("net_pct"), dimension_data.get("turnover_rate"))
        policy = self.score_policy(dimension_data.get("policy_count", 0), dimension_data.get("policy_level", "unknown"))

        total = inv["score"] + profit["score"] + demand["score"] + capital["score"] + policy["score"]

        if total >= 70:
            suggestion = "超配"
        elif total >= 50:
            suggestion = "标配"
        else:
            suggestion = "低配"

        # 生成催化剂
        catalysts = []
        if inv["score"] >= 25:
            catalysts.append(f"库存周期: {inv.get('phase', '')}")
        if profit["score"] >= 15:
            catalysts.append(f"盈利回升: ROE={dimension_data.get('roe', 'N/A')}")
        if demand["score"] >= 15:
            catalysts.append(f"需求旺盛: 同比+{dimension_data.get('sales_yoy', 0)}%")
        if capital["score"] >= 12:
            catalysts.append("资金持续流入")
        if policy["score"] >= 10:
            catalysts.append("政策利好")

        return {
            "score": total,
            "suggestion": suggestion,
            "inventory_cycle": inv.get("phase", "-"),
            "inventory_score": inv["score"],
            "profit_trend": profit.get("detail", "-"),
            "profit_score": profit["score"],
            "demand_growth": demand.get("detail", "-"),
            "demand_score": demand["score"],
            "capital_flow": capital.get("detail", "-"),
            "capital_score": capital["score"],
            "policy_support": policy.get("detail", "-"),
            "policy_score": policy["score"],
            "catalysts": catalysts,
            "five_dimensions": {
                "库存周期": inv,
                "盈利趋势": profit,
                "需求增速": demand,
                "资金流向": capital,
                "政策支持": policy,
            },
            "is_quick": False,
        }

    def evaluate_all(self, industries_dimension_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评分所有行业并排序
        industries_dimension_data: { 行业名: {维度数据} }
        """
        results = []
        for industry_name, data in industries_dimension_data.items():
            if data.get("is_quick"):
                # 已有快速评分，直接用
                scored = data
            else:
                scored = self.full_score_with_details(data)
            scored["industry_name"] = industry_name
            results.append(scored)

        # 按评分排序
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 添加排名
        for idx, item in enumerate(results):
            item["rank"] = idx + 1

        return results
