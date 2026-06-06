"""
个股体检评分引擎
五维度评分：主营业务(30) + 利润含金量(25) + 毛利率(20) + 信披(15) + 供应链(10)
总分 0~100，输出 可关注/谨慎/回避
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("stock_health_score_engine")


class StockHealthScoreEngine:
    """个股体检评分引擎"""

    WEIGHTS = {
        "主营业务匹配度": 30,
        "利润含金量": 25,
        "毛利率合理性": 20,
        "信披记录": 15,
        "供应链验证": 10,
    }

    def score_main_business(self, main_ratio: float = None) -> Dict[str, Any]:
        """主营业务匹配度评分（0~30）"""
        if main_ratio is None:
            return {"score": 15, "max": 30, "detail": "缺少主营数据，给予中间分"}

        if main_ratio >= 80:
            return {"score": 30, "max": 30, "detail": f"主营集中度{main_ratio}%，业务清晰"}
        elif main_ratio >= 60:
            return {"score": 20, "max": 30, "detail": f"主营集中度{main_ratio}%，存在一定多元化"}
        else:
            return {"score": 5, "max": 30, "detail": f"主营集中度仅{main_ratio}%，业务分散需警惕"}

    def score_profit_quality(self, deducted_ratio: float = None, trend: str = "unknown") -> Dict[str, Any]:
        """利润含金量评分（0~25）"""
        if deducted_ratio is None:
            return {"score": 12, "max": 25, "detail": "缺少利润质量数据"}

        if deducted_ratio >= 90:
            score = 25 if trend != "down" else 20
            return {"score": score, "max": 25, "detail": f"扣非比{deducted_ratio}%，利润质量优秀"}
        elif deducted_ratio >= 70:
            score = 15 if trend != "down" else 12
            return {"score": score, "max": 25, "detail": f"扣非比{deducted_ratio}%，部分依赖非经常性损益"}
        else:
            return {"score": 5, "max": 25, "detail": f"扣非比仅{deducted_ratio}%，严重依赖非经常性损益"}

    def score_gross_margin(self, stock_margin: float = None, industry_avg: float = None) -> Dict[str, Any]:
        """毛利率合理性评分（0~20）"""
        if stock_margin is None or industry_avg is None:
            return {"score": 10, "max": 20, "detail": "缺少毛利率数据"}

        if industry_avg == 0:
            return {"score": 10, "max": 20, "detail": "行业均值为0，无法比较"}

        deviation = abs(stock_margin - industry_avg) / industry_avg * 100

        if deviation < 15:
            return {"score": 20, "max": 20, "detail": f"毛利率{stock_margin}%，偏离行业均值{deviation:.1f}%，正常范围"}
        elif deviation < 20:
            return {"score": 10, "max": 20, "detail": f"毛利率{stock_margin}%，偏离行业均值{deviation:.1f}%，需确认技术壁垒"}
        elif deviation < 50:
            return {"score": 5, "max": 20, "detail": f"毛利率{stock_margin}%，偏离行业均值{deviation:.1f}%，偏离较大"}
        else:
            return {"score": 0, "max": 20, "detail": f"毛利率{stock_margin}%，偏离行业均值{deviation:.1f}%，异常偏高需警惕"}

    def score_disclosure(self, penalty_count: int = 0, inquiry_count: int = 0, investigation: bool = False) -> Dict[str, Any]:
        """信披记录评分（0~15）"""
        if investigation:
            return {"score": 0, "max": 15, "detail": "存在立案调查记录，信披风险极高"}
        elif penalty_count > 0:
            return {"score": 3, "max": 15, "detail": f"存在{penalty_count}次处罚记录"}
        elif inquiry_count > 0:
            return {"score": 10, "max": 15, "detail": f"收到{inquiry_count}次问询函，无处罚"}
        else:
            return {"score": 15, "max": 15, "detail": "无处罚、无问询，信披记录良好"}

    def score_supply_chain(self, in_supply_chain: bool = False, has_contract: bool = False) -> Dict[str, Any]:
        """供应链验证评分（0~10）"""
        if in_supply_chain and has_contract:
            return {"score": 10, "max": 10, "detail": "进入龙头供应链且有合同验证"}
        elif in_supply_chain:
            return {"score": 5, "max": 10, "detail": "进入供应链但无具体合同验证"}
        else:
            return {"score": 3, "max": 10, "detail": "供应链关系未验证"}

    def apply_deductions(self, base_score: float, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用扣分项"""
        deduction = 0
        deduction_details = []

        # 解禁压力
        unlock_ratio = data.get("unlock_pressure", {}).get("unlock_ratio", 0)
        if unlock_ratio > 20:
            deduction += 10
            deduction_details.append({
                "rule": "解禁压力",
                "severity": "高",
                "message": f"近期解禁比例{unlock_ratio:.1f}%，超过20%警戒线",
            })
        elif unlock_ratio > 10:
            deduction += 5
            deduction_details.append({
                "rule": "解禁压力",
                "severity": "中",
                "message": f"近期解禁比例{unlock_ratio:.1f}%",
            })

        return {
            "deduction": deduction,
            "details": deduction_details,
        }

    def detect_alerts(self, data: Dict[str, Any], scores: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """检测排雷预警"""
        alerts = []

        # 毛利率异常
        margin_data = data.get("gross_margin", {})
        margin_score = scores.get("毛利率合理性", {})
        if margin_score.get("score", 20) <= 5:
            alerts.append({
                "rule": "毛利率异常偏离",
                "severity": "高",
                "message": margin_score.get("detail", "毛利率偏离行业均值过大"),
            })

        # 利润质量差
        profit_data = data.get("profit_quality", {})
        profit_score = scores.get("利润含金量", {})
        if profit_data.get("deducted_ratio") is not None and profit_data["deducted_ratio"] < 70:
            alerts.append({
                "rule": "利润含金量低",
                "severity": "高",
                "message": f"扣非净利润占比仅{profit_data['deducted_ratio']}%，利润质量堪忧",
            })

        # 信披风险
        disclosure_data = data.get("disclosure", {})
        if disclosure_data.get("investigation"):
            alerts.append({
                "rule": "立案调查",
                "severity": "高",
                "message": "公司存在立案调查记录，建议回避",
            })
        elif disclosure_data.get("penalty_count", 0) > 0:
            alerts.append({
                "rule": "处罚记录",
                "severity": "中",
                "message": f"存在{disclosure_data['penalty_count']}次处罚记录",
            })

        # 主营分散
        main_data = data.get("main_business", {})
        if main_data.get("main_ratio") is not None and main_data["main_ratio"] < 60:
            alerts.append({
                "rule": "主营业务分散",
                "severity": "中",
                "message": f"主营集中度仅{main_data['main_ratio']}%，业务结构分散",
            })

        # 解禁压力
        unlock_ratio = data.get("unlock_pressure", {}).get("unlock_ratio", 0)
        if unlock_ratio > 20:
            alerts.append({
                "rule": "解禁压力",
                "severity": "高",
                "message": f"近期解禁比例{unlock_ratio:.1f}%",
            })

        return alerts

    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算个股体检总分
        data: fetch_all() 返回的完整数据
        """
        main_biz = data.get("main_business", {})
        profit = data.get("profit_quality", {})
        margin = data.get("gross_margin", {})
        disclosure = data.get("disclosure", {})
        supply = data.get("supply_chain", {})

        # 五维度评分
        main_score = self.score_main_business(main_biz.get("main_ratio"))
        profit_score = self.score_profit_quality(profit.get("deducted_ratio"), profit.get("trend", "unknown"))
        margin_score = self.score_gross_margin(margin.get("gross_margin"), margin.get("industry_avg"))
        disclosure_score = self.score_disclosure(
            disclosure.get("penalty_count", 0),
            disclosure.get("inquiry_count", 0),
            disclosure.get("investigation", False),
        )
        supply_score = self.score_supply_chain(
            supply.get("in_supply_chain", False),
            supply.get("has_contract", False),
        )

        scores = {
            "主营业务匹配度": main_score,
            "利润含金量": profit_score,
            "毛利率合理性": margin_score,
            "信披记录": disclosure_score,
            "供应链验证": supply_score,
        }

        base_score = sum(s["score"] for s in scores.values())

        # 扣分
        deduction_result = self.apply_deductions(base_score, data)
        deduction = deduction_result["deduction"]

        total_score = max(0, base_score - deduction)

        # 结论
        if total_score >= 80:
            conclusion = "可关注"
        elif total_score >= 60:
            conclusion = "谨慎"
        else:
            conclusion = "回避"

        # 风险等级
        if total_score >= 80:
            risk_level = "低"
        elif total_score >= 60:
            risk_level = "中"
        else:
            risk_level = "高"

        # 预警
        alerts = self.detect_alerts(data, scores)
        alerts.extend(deduction_result["details"])

        return {
            "main_business_score": main_score["score"],
            "main_business_detail": main_score,
            "profit_quality_score": profit_score["score"],
            "profit_quality_detail": profit_score,
            "gross_margin_score": margin_score["score"],
            "gross_margin_detail": margin_score,
            "disclosure_score": disclosure_score["score"],
            "disclosure_detail": disclosure_score,
            "supply_chain_score": supply_score["score"],
            "supply_chain_detail": supply_score,
            "deduction": deduction,
            "total_score": total_score,
            "risk_level": risk_level,
            "conclusion": conclusion,
            "alerts": alerts,
        }
