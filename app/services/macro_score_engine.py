"""
宏观评分引擎
基于宏观经济指标，计算宏观环境评分（0~100）
输出"可积极参与 / 谨慎试仓 / 防守观望"结论
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("macro_score_engine")


class MacroScoreEngine:
    """宏观评分引擎"""

    # 各指标权重（总和 1.0）
    WEIGHTS = {
        "PMI": 0.20,
        "非制造业PMI": 0.00,  # 辅助参考，不参与评分
        "社融存量同比": 0.20,
        "CPI": 0.10,
        "PPI": 0.10,
        "M2": 0.10,
        "DR007": 0.15,
        "北向资金": 0.15,
        "人民币汇率": 0.00,  # 辅助参考，不参与评分
    }

    def score_pmi(self, value: float) -> Dict[str, Any]:
        """PMI 评分（0~100）"""
        if value > 51:
            score, detail = 100, "扩张区间，经济向好"
        elif value > 50:
            score, detail = 75, "略高于荣枯线，温和扩张"
        elif value > 49:
            score, detail = 45, "略低于荣枯线，温和收缩"
        else:
            score, detail = 10, "收缩区间，经济承压"
        return {"score": score, "weight": self.WEIGHTS.get("PMI", 0.2), "direction": "好" if value > 50 else "坏", "detail": detail, "value": value}

    def score_social_financing(self, value: float) -> Dict[str, Any]:
        """社融存量同比评分"""
        if value > 12:
            score, detail = 100, "宽信用，流动性充裕"
        elif value > 10:
            score, detail = 80, "信用合理扩张"
        elif value > 8:
            score, detail = 50, "信用温和"
        else:
            score, detail = 10, "紧信用，流动性偏紧"
        return {"score": score, "weight": self.WEIGHTS.get("社融存量同比", 0.2), "direction": "好" if value > 10 else "坏", "detail": detail, "value": value}

    def score_cpi(self, value: float) -> Dict[str, Any]:
        """CPI 评分"""
        if 2 <= value <= 3:
            score, detail = 100, "温和通胀，经济健康"
        elif 1 <= value < 2 or 3 < value <= 4:
            score, detail = 60, "偏离温和区间"
        else:
            score, detail = 10, "通缩或过热风险"
        return {"score": score, "weight": self.WEIGHTS.get("CPI", 0.1), "direction": "好" if 2 <= value <= 3 else "坏", "detail": detail, "value": value}

    def score_ppi(self, value: float) -> Dict[str, Any]:
        """PPI 评分"""
        if value > 0:
            score, detail = 80, "工业品价格回升，需求旺盛"
        elif value > -2:
            score, detail = 40, "工业品价格小幅回落"
        else:
            score, detail = 10, "工业品价格持续下降，需求疲软"
        return {"score": score, "weight": self.WEIGHTS.get("PPI", 0.1), "direction": "好" if value > 0 else "坏", "detail": detail, "value": value}

    def score_m2(self, value: float) -> Dict[str, Any]:
        """M2 同比评分（简化版，GDP增速取固定值6%估算）"""
        gdp_growth_est = 6.0  # 名义GDP增速估算
        if value > gdp_growth_est + 2:
            score, detail = 100, "货币宽松，M2显著高于GDP增速"
        elif value > gdp_growth_est:
            score, detail = 70, "货币适度宽松"
        elif value > gdp_growth_est - 2:
            score, detail = 40, "货币增速放缓"
        else:
            score, detail = 10, "货币偏紧，M2低于GDP增速"
        return {"score": score, "weight": self.WEIGHTS.get("M2", 0.1), "direction": "好" if value > gdp_growth_est else "坏", "detail": detail, "value": value}

    def score_dr007(self, value: float) -> Dict[str, Any]:
        """DR007 评分（越低越宽松）"""
        # 当前7天逆回购政策利率约1.5%
        policy_rate = 1.5
        spread = value - policy_rate
        if spread < -0.3:
            score, detail = 100, f"非常宽松（DR007低于政策利率{abs(spread):.2f}个百分点）"
        elif spread < 0:
            score, detail = 80, f"偏宽松（DR007低于政策利率{abs(spread):.2f}个百分点）"
        elif spread < 0.3:
            score, detail = 50, f"中性偏紧（DR007高于政策利率{spread:.2f}个百分点）"
        else:
            score, detail = 10, f"偏紧（DR007高于政策利率{spread:.2f}个百分点）"
        return {"score": score, "weight": self.WEIGHTS.get("DR007", 0.15), "direction": "好" if spread < 0 else "坏", "detail": detail, "value": value, "spread": spread}

    def score_northbound(self, value: float) -> Dict[str, Any]:
        """北向资金评分"""
        if value > 50:
            score, detail = 100, f"大幅净流入{value:.1f}亿，外资积极"
        elif value > 30:
            score, detail = 80, f"净流入{value:.1f}亿，外资偏乐观"
        elif value > 0:
            score, detail = 50, f"小幅净流入{value:.1f}亿"
        elif value > -30:
            score, detail = 30, f"小幅净流出{abs(value):.1f}亿"
        else:
            score, detail = 10, f"大幅净流出{abs(value):.1f}亿，外资撤离"
        return {"score": score, "weight": self.WEIGHTS.get("北向资金", 0.15), "direction": "好" if value > 0 else "坏", "detail": detail, "value": value}

    def get_scorer(self, indicator_name: str):
        """根据指标名获取对应的评分函数"""
        scorers = {
            "PMI": self.score_pmi,
            "CPI": self.score_cpi,
            "PPI": self.score_ppi,
            "M2": self.score_m2,
            "社融存量同比": self.score_social_financing,
            "DR007": self.score_dr007,
            "北向资金": self.score_northbound,
        }
        return scorers.get(indicator_name)

    def calculate(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """
        计算宏观综合评分
        indicators: { "PMI": 50.4, "CPI": 2.1, ... }
        """
        details = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for name, value in indicators.items():
            scorer = self.get_scorer(name)
            if scorer is None:
                continue
            result = scorer(value)
            details[name] = result
            total_weighted_score += result["score"] * result["weight"]
            total_weight += result["weight"]

        if total_weight == 0:
            return {"total_score": 0, "level": "数据不足", "details": details, "alerts": []}

        total_score = round(total_weighted_score / total_weight, 1)

        # 判定等级
        if total_score > 70:
            level = "可积极参与"
        elif total_score >= 40:
            level = "谨慎试仓"
        else:
            level = "防守观望"

        # 检测异常
        alerts = self._detect_anomalies(indicators, details)

        return {
            "total_score": total_score,
            "level": level,
            "details": details,
            "alerts": alerts,
        }

    def _detect_anomalies(self, indicators: Dict[str, float], details: Dict) -> List[Dict]:
        """检测异常指标"""
        alerts = []

        # PMI 连续低于 49
        pmi = indicators.get("PMI")
        if pmi and pmi < 49:
            alerts.append({
                "indicator": "PMI",
                "severity": "高",
                "message": f"PMI={pmi}，制造业持续收缩",
            })

        # 社融骤降
        shrzgm = indicators.get("社融存量同比")
        if shrzgm and shrzgm < 8:
            alerts.append({
                "indicator": "社融存量同比",
                "severity": "高",
                "message": f"社融同比={shrzgm}%，信用收缩明显",
            })

        # CPI 通缩
        cpi = indicators.get("CPI")
        if cpi is not None and cpi < 0:
            alerts.append({
                "indicator": "CPI",
                "severity": "高",
                "message": f"CPI={cpi}%，出现通缩信号",
            })

        # 北向资金大幅流出
        northbound = indicators.get("北向资金")
        if northbound is not None and northbound < -50:
            alerts.append({
                "indicator": "北向资金",
                "severity": "中",
                "message": f"北向资金净流出{abs(northbound):.1f}亿，外资大幅撤离",
            })

        # DR007 偏紧
        dr007 = indicators.get("DR007")
        if dr007 and dr007 > 2.0:
            alerts.append({
                "indicator": "DR007",
                "severity": "中",
                "message": f"DR007={dr007}%，流动性偏紧",
            })

        return alerts
