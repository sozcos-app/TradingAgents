"""
统一API响应格式工具
"""
import math
from datetime import datetime
from typing import Any, Optional, Dict
from app.utils.timezone import now_tz


def _sanitize_floats(obj):
    """递归清理不合法的浮点数（NaN、inf），替换为 None 以保证 JSON 序列化不出错"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    return obj


def ok(data: Any = None, message: str = "ok") -> Dict[str, Any]:
    """标准成功响应
    返回结构：{"success": True, "data": data, "message": message, "timestamp": ...}
    """
    return {
        "success": True,
        "data": _sanitize_floats(data),
        "message": message,
        "timestamp": now_tz().isoformat()
    }


def fail(message: str = "error", code: int = 500, data: Any = None) -> Dict[str, Any]:
    """标准失败响应（一般错误仍建议用 HTTPException 抛出，此函数用于业务失败场景）"""
    return {
        "success": False,
        "data": _sanitize_floats(data),
        "message": message,
        "code": code,
        "timestamp": now_tz().isoformat()
    }
