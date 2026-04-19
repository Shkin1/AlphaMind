"""
Financial Data Tool - 财务数据获取工具

使用AkShare获取财务报表和估值数据
"""

import akshare as ak
import pandas as pd
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class FinancialDataTool:
    """财务数据工具"""

    def __init__(self):
        pass

    def get_financial_summary(self, stock_code: str) -> Dict:
        """
        获取财务概况

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 财务概况
        """
        try:
            # 获取主要财务指标
            df = ak.stock_financial_abstract_em(symbol=stock_code)

            if df.empty:
                return {}

            # 取最近一期数据
            latest = df.iloc[0]

            return {
                "report_date": str(latest.get('报告期', '')),
                "revenue": float(latest.get('营业收入', 0)) if pd.notna(latest.get('营业收入')) else 0,
                "net_profit": float(latest.get('净利润', 0)) if pd.notna(latest.get('净利润')) else 0,
                "total_assets": float(latest.get('总资产', 0)) if pd.notna(latest.get('总资产')) else 0,
                "total_liabilities": float(latest.get('总负债', 0)) if pd.notna(latest.get('总负债')) else 0,
                "equity": float(latest.get('净资产', 0)) if pd.notna(latest.get('净资产')) else 0,
            }

        except Exception as e:
            logger.error(f"获取财务概况失败: {e}")
            return {}

    def get_valuation_metrics(self, stock_code: str) -> Dict:
        """
        获取估值指标

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 估值指标
        """
        try:
            # 获取实时行情中的估值数据
            df = ak.stock_zh_a_spot_em()
            result = df[df['代码'] == stock_code]

            if result.empty:
                return {}

            row = result.iloc[0]

            pe = float(row.get('市盈率-动态', 0)) if pd.notna(row.get('市盈率-动态')) else 0
            pb = float(row.get('市净率', 0)) if pd.notna(row.get('市净率')) else 0
            total_mv = float(row.get('总市值', 0)) if pd.notna(row.get('总市值')) else 0
            circ_mv = float(row.get('流通市值', 0)) if pd.notna(row.get('流通市值')) else 0

            return {
                "PE_TTM": round(pe, 2),
                "PB": round(pb, 2),
                "total_market_value": round(total_mv / 1e8, 2),  # 亿元
                "circulating_market_value": round(circ_mv / 1e8, 2),  # 亿元
                "market_cap": round(total_mv / 1e8, 2),  # 简化
            }

        except Exception as e:
            logger.error(f"获取估值指标失败: {e}")
            return {}

    def get_profitability_metrics(self, stock_code: str) -> Dict:
        """
        获取盈利能力指标

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 盈利能力指标
        """
        try:
            # 获取财务指标
            df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")

            if df.empty:
                return {}

            latest = df.iloc[0]

            roe = float(latest.get('净资产收益率', 0)) if pd.notna(latest.get('净资产收益率')) else 0
            roa = float(latest.get('总资产收益率', 0)) if pd.notna(latest.get('总资产收益率')) else 0
            gross_margin = float(latest.get('销售毛利率', 0)) if pd.notna(latest.get('销售毛利率')) else 0
            net_margin = float(latest.get('销售净利率', 0)) if pd.notna(latest.get('销售净利率')) else 0

            return {
                "ROE": round(roe, 2),
                "ROA": round(roa, 2),
                "gross_margin": round(gross_margin, 2),
                "net_margin": round(net_margin, 2),
            }

        except Exception as e:
            logger.error(f"获取盈利能力指标失败: {e}")
            return {}

    def get_full_data(self, stock_code: str) -> Dict:
        """
        获取完整数据（用于顾问分析）

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 完整数据
        """
        # 股票基本信息
        from .stock_data import stock_tool
        stock_info = stock_tool.get_stock_info(stock_code)

        # 技术指标
        tech_indicators = stock_tool.get_technical_indicators(stock_code)

        # 财务数据
        financial_summary = self.get_financial_summary(stock_code)
        valuation = self.get_valuation_metrics(stock_code)
        profitability = self.get_profitability_metrics(stock_code)

        # 合并数据
        return {
            "code": stock_info.get("code", stock_code),
            "name": stock_info.get("name", "未知"),
            "price": stock_info.get("price", 0),
            "change_pct": stock_info.get("change_pct", 0),
            **tech_indicators,
            **valuation,
            **financial_summary,
            **profitability,
            "data_source": "AkShare",
            "update_time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        }


# 创建全局实例
financial_tool = FinancialDataTool()