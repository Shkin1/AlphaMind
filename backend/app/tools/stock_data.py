"""
Stock Data Tool - 股票数据获取工具

使用AkShare获取A股数据，失败时使用模拟数据
"""

import akshare as ak
import pandas as pd
from typing import Dict, Optional, List
import logging
import time
import random

logger = logging.getLogger(__name__)


class StockDataTool:
    """股票数据工具"""

    # 常见股票模拟数据
    MOCK_DATA = {
        "000651": {"name": "格力电器", "code": "000651", "price": 36.95, "change_pct": -0.5},
        "600519": {"name": "贵州茅台", "code": "600519", "price": 1688.0, "change_pct": 1.2},
        "000858": {"name": "五粮液", "code": "000858", "price": 145.0, "change_pct": 0.8},
        "002594": {"name": "比亚迪", "code": "002594", "price": 245.0, "change_pct": 2.5},
        "300750": {"name": "宁德时代", "code": "300750", "price": 185.0, "change_pct": -1.0},
        "600036": {"name": "招商银行", "code": "600036", "price": 33.5, "change_pct": 0.3},
        "601318": {"name": "中国平安", "code": "601318", "price": 42.0, "change_pct": -0.8},
    }

    def __init__(self):
        pass

    def search_stock(self, keyword: str, max_retries: int = 2) -> List[Dict]:
        """搜索股票"""
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_spot_em()
                results = df[
                    df['代码'].str.contains(keyword, na=False) |
                    df['名称'].str.contains(keyword, na=False)
                ]

                stocks = []
                for _, row in results.head(10).iterrows():
                    stocks.append({
                        "code": row['代码'],
                        "name": row['名称'],
                        "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    })
                return stocks

            except Exception as e:
                logger.error(f"搜索股票失败(尝试{attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        # 返回模拟数据
        logger.warning("使用模拟股票数据")
        return self._mock_search(keyword)

    def _mock_search(self, keyword: str) -> List[Dict]:
        """模拟搜索"""
        results = []
        for code, data in self.MOCK_DATA.items():
            if keyword in data["name"] or keyword in code:
                results.append(data)
        return results if results else [{"code": "000001", "name": "示例股票", "price": 10.0}]

    def get_stock_info(self, stock_code: str, max_retries: int = 2) -> Dict:
        """获取股票基本信息"""
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_spot_em()

                if stock_code.isdigit() and len(stock_code) == 6:
                    result = df[df['代码'] == stock_code]
                else:
                    result = df[df['名称'].str.contains(stock_code, na=False)]

                if result.empty:
                    return self._mock_stock_info(stock_code)

                row = result.iloc[0]
                return {
                    "code": row['代码'],
                    "name": row['名称'],
                    "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    "change_pct": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                    "change_amount": float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                    "volume": float(row['成交量']) if pd.notna(row['成交量']) else 0,
                    "amount": float(row['成交额']) if pd.notna(row['成交额']) else 0,
                    "high": float(row['最高']) if pd.notna(row['最高']) else 0,
                    "low": float(row['最低']) if pd.notna(row['最低']) else 0,
                    "open": float(row['今开']) if pd.notna(row['今开']) else 0,
                    "pre_close": float(row['昨收']) if pd.notna(row['昨收']) else 0,
                }

            except Exception as e:
                logger.error(f"获取股票信息失败(尝试{attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        return self._mock_stock_info(stock_code)

    def _mock_stock_info(self, stock_code: str) -> Dict:
        """模拟股票信息"""
        if stock_code in self.MOCK_DATA:
            data = self.MOCK_DATA[stock_code]
            return {
                "code": data["code"],
                "name": data["name"],
                "price": data["price"],
                "change_pct": data["change_pct"],
                "change_amount": data["price"] * data["change_pct"] / 100,
                "volume": 10000000,
                "amount": 100000000,
                "high": data["price"] * 1.02,
                "low": data["price"] * 0.98,
                "open": data["price"],
                "pre_close": data["price"] / (1 + data["change_pct"]/100),
            }
        return {"code": stock_code, "name": "示例股票", "price": 10.0, "change_pct": 0}

    def get_technical_indicators(self, stock_code: str) -> Dict:
        """计算技术指标"""
        history = self.get_stock_history(stock_code, days=100)

        if not history:
            return self._mock_technical_indicators(stock_code)

        closes = [h['close'] for h in history]

        # MA均线
        ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else closes[-1]
        ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else closes[-1]
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else closes[-1]

        # 判断趋势
        trend = "震荡"
        if closes[-1] > ma5 and ma5 > ma10 and ma10 > ma20:
            trend = "上升趋势"
        elif closes[-1] < ma5 and ma5 < ma10 and ma10 < ma20:
            trend = "下降趋势"

        return {
            "MA5": round(ma5, 2),
            "MA10": round(ma10, 2),
            "MA20": round(ma20, 2),
            "MA60": round(ma60, 2),
            "trend": trend,
            "current_price": closes[-1],
            "support_level": round(min(closes[-20:]), 2),
            "resistance_level": round(max(closes[-20:]), 2),
        }

    def _mock_technical_indicators(self, stock_code: str) -> Dict:
        """模拟技术指标"""
        base_price = self.MOCK_DATA.get(stock_code, {}).get("price", 10.0)
        return {
            "MA5": round(base_price * 0.99, 2),
            "MA10": round(base_price * 0.98, 2),
            "MA20": round(base_price * 0.97, 2),
            "MA60": round(base_price * 0.95, 2),
            "trend": "震荡",
            "current_price": base_price,
            "support_level": round(base_price * 0.92, 2),
            "resistance_level": round(base_price * 1.08, 2),
        }

    def get_stock_history(self, stock_code: str, period: str = "daily",
                          days: int = 60) -> List[Dict]:
        """获取股票历史数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=stock_code, period=period, adjust="qfq")

            if df.empty:
                return self._mock_history(stock_code, days)

            df = df.tail(days)

            history = []
            for _, row in df.iterrows():
                history.append({
                    "date": str(row['日期']),
                    "open": float(row['开盘']),
                    "close": float(row['收盘']),
                    "high": float(row['最高']),
                    "low": float(row['最低']),
                    "volume": float(row['成交量']),
                    "amount": float(row['成交额']),
                    "change_pct": float(row['涨跌幅']) if '涨跌幅' in row else 0,
                })

            return history

        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return self._mock_history(stock_code, days)

    def _mock_history(self, stock_code: str, days: int) -> List[Dict]:
        """模拟历史数据"""
        base_price = self.MOCK_DATA.get(stock_code, {}).get("price", 10.0)
        history = []
        for i in range(days):
            date_offset = days - i
            # 模拟波动
            price = base_price * (1 + random.uniform(-0.03, 0.03))
            history.append({
                "date": f"2024-{(12 - date_offset//30):02d}-{(30 - date_offset%30):02d}",
                "open": round(price * 0.99, 2),
                "close": round(price, 2),
                "high": round(price * 1.02, 2),
                "low": round(price * 0.98, 2),
                "volume": 10000000,
                "amount": 100000000,
                "change_pct": random.uniform(-2, 2),
            })
        return history

    def get_market_summary(self) -> Dict:
        """获取市场概况"""
        try:
            sh_df = ak.stock_zh_index_daily(symbol="sh000001")
            sh_latest = sh_df.iloc[-1] if not sh_df.empty else None

            return {
                "sh_index": {
                    "code": "000001",
                    "name": "上证指数",
                    "price": float(sh_latest['close']) if sh_latest is not None else 3100,
                },
                "market_status": "正常"
            }

        except Exception as e:
            logger.error(f"获取市场概况失败: {e}")
            return {"sh_index": {"price": 3100}, "market_status": "模拟"}


stock_tool = StockDataTool()