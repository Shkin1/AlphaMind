"""
数据采集模块 - Data Collector

提供两种采集方式：
1. BochaWebCollector - 博查AI网页搜索采集
2. AkshareCollector - Akshare金融数据采集

架构设计：
- BaseCollector: 抽象基类，定义统一接口
- 各采集器继承基类，实现具体逻辑
- 采集结果统一为CollectedData格式
"""

import asyncio
import logging
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CollectedData:
    """采集数据统一格式"""
    source: str                    # 数据来源 (bocha/akshare)
    data_type: str                 # 数据类型 (news/stock_price/financials/...)
    content: Any                   # 具体数据内容
    metadata: Dict = field(default_factory=dict)  # 元数据（时间、来源URL等）
    collected_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None    # 错误信息

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "source": self.source,
            "data_type": self.data_type,
            "content": self.content,
            "metadata": self.metadata,
            "collected_at": self.collected_at.isoformat(),
            "error": self.error
        }


class BaseCollector(ABC):
    """采集器基类"""

    name: str = "base"
    description: str = "基础采集器"

    @abstractmethod
    async def collect(self, query: str, **kwargs) -> CollectedData:
        """
        执行采集

        Args:
            query: 查询内容（股票名称、关键词等）
            **kwargs: 额外参数

        Returns:
            CollectedData: 采集结果
        """
        pass

    @abstractmethod
    async def collect_batch(self, queries: List[str], **kwargs) -> List[CollectedData]:
        """
        批量采集

        Args:
            queries: 查询列表
            **kwargs: 额外参数

        Returns:
            List[CollectedData]: 采集结果列表
        """
        pass

    def is_available(self) -> bool:
        """检查采集器是否可用"""
        return True


class BochaWebCollector(BaseCollector):
    """
    博查AI网页搜索采集器

    用于采集：
    - 股票相关新闻
    - 研报摘要
    - 行业动态
    - 公司公告
    """

    name = "bocha"
    description = "博查AI网页搜索采集"

    def __init__(self):
        self.api_key = os.getenv("BOCHA_API_KEY", "")
        self.api_base = os.getenv("BOCHA_API_BASE", "https://api.bocha.io/v1")

    def is_available(self) -> bool:
        """检查API Key是否配置"""
        return bool(self.api_key)

    async def collect(self, query: str, **kwargs) -> CollectedData:
        """
        执行网页搜索采集

        Args:
            query: 搜索关键词（如 "格力电器 最新新闻"）
            data_type: 数据类型，可选值: news/report/announcement
        """
        data_type = kwargs.get("data_type", "news")

        if not self.is_available():
            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=None,
                error="博查API Key未配置，请在.env中设置BOCHA_API_KEY"
            )

        try:
            import aiohttp

            # 构建请求
            url = f"{self.api_base}/search"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "search_type": "web",  # 网页搜索
                "max_results": kwargs.get("max_results", 5)
            }

            logger.info(f"[博查] 搜索: {query}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[博查] API错误: {resp.status} - {error_text}")
                        return CollectedData(
                            source=self.name,
                            data_type=data_type,
                            content=None,
                            error=f"API错误: {resp.status}"
                        )

                    result = await resp.json()

            # 解析结果
            results = result.get("results", [])
            if not results:
                return CollectedData(
                    source=self.name,
                    data_type=data_type,
                    content={"summary": f"未找到'{query}'相关内容", "items": []},
                    metadata={"query": query}
                )

            # 提取关键信息
            items = []
            for item in results[:5]:
                items.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", "")
                })

            content = {
                "query": query,
                "items": items,
                "summary": self._summarize_results(items)
            }

            logger.info(f"[博查] 采集成功: {len(items)}条")

            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=content,
                metadata={"query": query, "total_results": len(results)}
            )

        except asyncio.TimeoutError:
            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=None,
                error="请求超时"
            )
        except Exception as e:
            logger.error(f"[博查] 采集失败: {e}")
            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=None,
                error=str(e)
            )

    async def collect_batch(self, queries: List[str], **kwargs) -> List[CollectedData]:
        """批量采集"""
        results = []
        for query in queries:
            result = await self.collect(query, **kwargs)
            results.append(result)
        return results

    def _summarize_results(self, items: List[Dict]) -> str:
        """总结搜索结果"""
        if not items:
            return "无相关信息"

        snippets = [item.get("snippet", "") for item in items if item.get("snippet")]
        if snippets:
            # 简单拼接摘要
            return " | ".join(snippets[:3])
        return f"找到{len(items)}条相关信息"


class AkshareCollector(BaseCollector):
    """
    Akshare金融数据采集器

    用于采集：
    - 股票实时行情
    - 历史行情
    - 财务数据
    - 行业数据
    """

    name = "akshare"
    description = "Akshare金融数据采集"

    # 股票代码映射（简化版）
    STOCK_CODE_MAP = {
        "格力": "000651",
        "格力电器": "000651",
        "茅台": "600519",
        "贵州茅台": "600519",
        "比亚迪": "002594",
        "宁德时代": "300750",
        "平安": "000001",
        "中国平安": "000001",
        "腾讯": "00700",  # 港股
        "招商银行": "600036",
        "五粮液": "000858",
        "美的": "000333",
        "美的集团": "000333",
        "海尔": "600690",
        "海尔智家": "600690",
    }

    def is_available(self) -> bool:
        """检查akshare是否安装"""
        try:
            import akshare
            return True
        except ImportError:
            return False

    async def collect(self, query: str, **kwargs) -> CollectedData:
        """
        采集股票数据

        Args:
            query: 股票名称或代码
            data_type: 数据类型: realtime/historical/financials
        """
        data_type = kwargs.get("data_type", "realtime")

        if not self.is_available():
            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=None,
                error="akshare未安装，请执行: pip install akshare"
            )

        try:
            import akshare as ak

            # 获取股票代码
            stock_code = self._get_stock_code(query)
            if not stock_code:
                # 尝试直接搜索
                stock_code = await self._search_stock_code(query)

            if not stock_code:
                return CollectedData(
                    source=self.name,
                    data_type=data_type,
                    content=None,
                    error=f"无法识别股票: {query}"
                )

            logger.info(f"[Akshare] 采集: {query} -> {stock_code}")

            # 根据数据类型采集
            if data_type == "realtime":
                content = await self._get_realtime_data(stock_code)
            elif data_type == "historical":
                content = await self._get_historical_data(stock_code, kwargs)
            elif data_type == "financials":
                content = await self._get_financials(stock_code)
            else:
                content = await self._get_realtime_data(stock_code)

            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=content,
                metadata={"stock_code": stock_code, "stock_name": query}
            )

        except Exception as e:
            logger.error(f"[Akshare] 采集失败: {e}")
            return CollectedData(
                source=self.name,
                data_type=data_type,
                content=None,
                error=str(e)
            )

    async def collect_batch(self, queries: List[str], **kwargs) -> List[CollectedData]:
        """批量采集"""
        results = []
        for query in queries:
            result = await self.collect(query, **kwargs)
            results.append(result)
        return results

    def _get_stock_code(self, name: str) -> Optional[str]:
        """从名称获取股票代码"""
        # 直接映射
        if name in self.STOCK_CODE_MAP:
            return self.STOCK_CODE_MAP[name]

        # 尝试部分匹配
        for key, code in self.STOCK_CODE_MAP.items():
            if key in name or name in key:
                return code

        # 如果已经是代码格式
        if name.isdigit() and len(name) == 6:
            return name

        return None

    async def _search_stock_code(self, name: str) -> Optional[str]:
        """搜索股票代码"""
        try:
            import akshare as ak

            # 使用股票查询接口
            df = ak.stock_zh_a_spot_em()
            result = df[df['名称'].str.contains(name, na=False)]
            if not result.empty:
                return result.iloc[0]['代码']
        except Exception as e:
            logger.error(f"[Akshare] 搜索股票失败: {e}")
        return None

    async def _get_realtime_data(self, code: str) -> Dict:
        """获取实时行情"""
        try:
            import akshare as ak

            # A股实时行情
            if code.startswith(('00', '30', '60')):
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == code]
                if not row.empty:
                    data = row.iloc[0]
                    return {
                        "name": data['名称'],
                        "code": code,
                        "price": float(data['最新价']),
                        "change_pct": float(data['涨跌幅']),
                        "volume": float(data['成交量']),
                        "amount": float(data['成交额']),
                        "high": float(data['最高']),
                        "low": float(data['最低']),
                        "open": float(data['今开']),
                        "pre_close": float(data['昨收']),
                    }

            return {"name": code, "code": code, "price": 0, "error": "未找到数据"}

        except Exception as e:
            logger.error(f"[Akshare] 实时数据获取失败: {e}")
            return {"name": code, "code": code, "price": 0, "error": str(e)}

    async def _get_historical_data(self, code: str, kwargs: Dict) -> Dict:
        """获取历史行情"""
        try:
            import akshare as ak
            import pandas as pd

            period = kwargs.get("period", "daily")
            days = kwargs.get("days", 30)

            df = ak.stock_zh_a_hist(symbol=code, period=period, adjust="qfq")

            # 取最近N天
            recent = df.tail(days)

            return {
                "name": code,
                "code": code,
                "data": recent.to_dict('records') if not recent.empty else [],
                "trend": self._analyze_trend(recent) if not recent.empty else "未知"
            }

        except Exception as e:
            logger.error(f"[Akshare] 历史数据获取失败: {e}")
            return {"name": code, "code": code, "error": str(e)}

    async def _get_financials(self, code: str) -> Dict:
        """获取财务数据"""
        try:
            import akshare as ak

            # 主要财务指标
            df = ak.stock_financial_analysis_indicator(symbol=code)

            if df.empty:
                return {"name": code, "code": code, "error": "无财务数据"}

            # 取最近一期
            latest = df.iloc[0]

            return {
                "name": code,
                "code": code,
                "roe": latest.get('净资产收益率', 0),
                "pe_ratio": latest.get('市盈率', 0),
                "pb_ratio": latest.get('市净率', 0),
                "gross_margin": latest.get('销售毛利率', 0),
                "net_margin": latest.get('销售净利率', 0),
            }

        except Exception as e:
            logger.error(f"[Akshare] 财务数据获取失败: {e}")
            return {"name": code, "code": code, "error": str(e)}

    def _analyze_trend(self, df) -> str:
        """分析趋势"""
        try:
            import pandas as pd

            if df.empty or len(df) < 5:
                return "数据不足"

            # 计算最近5日涨跌
            recent = df.tail(5)
            changes = recent['涨跌幅'].astype(float)

            avg_change = changes.mean()
            if avg_change > 1:
                return "上涨趋势"
            elif avg_change < -1:
                return "下跌趋势"
            else:
                return "横盘整理"
        except:
            return "未知"


class DataCollectorManager:
    """
    数据采集管理器

    统一管理所有采集器，提供便捷的采集接口
    """

    def __init__(self):
        self.collectors: Dict[str, BaseCollector] = {}
        self._register_collectors()

    def _register_collectors(self):
        """注册所有采集器"""
        self.collectors["bocha"] = BochaWebCollector()
        self.collectors["akshare"] = AkshareCollector()

    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """获取采集器"""
        return self.collectors.get(name)

    def list_collectors(self) -> List[Dict]:
        """列出所有采集器"""
        return [
            {
                "name": c.name,
                "description": c.description,
                "available": c.is_available()
            }
            for c in self.collectors.values()
        ]

    async def collect_all(self, query: str, **kwargs) -> Dict[str, CollectedData]:
        """
        使用所有可用采集器采集数据

        Args:
            query: 查询内容
            **kwargs: 额外参数

        Returns:
            Dict[str, CollectedData]: 各采集器的结果
        """
        results = {}

        for name, collector in self.collectors.items():
            if collector.is_available():
                try:
                    result = await collector.collect(query, **kwargs)
                    results[name] = result
                except Exception as e:
                    logger.error(f"[{name}] 采集异常: {e}")
                    results[name] = CollectedData(
                        source=name,
                        data_type=kwargs.get("data_type", "unknown"),
                        content=None,
                        error=str(e)
                    )
            else:
                results[name] = CollectedData(
                    source=name,
                    data_type=kwargs.get("data_type", "unknown"),
                    content=None,
                    error=f"采集器不可用"
                )

        return results

    async def collect_for_stock(self, stock_name: str) -> Dict:
        """
        为股票采集综合数据

        Args:
            stock_name: 股票名称

        Returns:
            Dict: 整合后的数据摘要
        """
        summary = {
            "stock_name": stock_name,
            "stock_data": None,
            "news": None,
            "collected_at": datetime.now().isoformat()
        }

        # 采集股票行情
        akshare_result = await self.collectors["akshare"].collect(stock_name, data_type="realtime")
        if akshare_result.content and not akshare_result.error:
            summary["stock_data"] = akshare_result.content

        # 采集新闻资讯
        bocha_result = await self.collectors["bocha"].collect(
            f"{stock_name} 最新动态 研报",
            data_type="news"
        )
        if bocha_result.content and not bocha_result.error:
            summary["news"] = bocha_result.content

        return summary


# 全局管理器实例
collector_manager = DataCollectorManager()