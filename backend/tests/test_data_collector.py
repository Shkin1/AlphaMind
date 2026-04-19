"""
数据采集模块测试用例

测试：
1. 基础功能测试
2. 博查采集器测试
3. Akshare采集器测试
4. 管理器测试
5. 集成测试
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.data_collector import (
    BaseCollector,
    BochaWebCollector,
    AkshareCollector,
    DataCollectorManager,
    CollectedData,
    collector_manager
)


class TestCollectedData:
    """测试CollectedData数据结构"""

    def test_create_collected_data(self):
        """测试创建采集数据"""
        data = CollectedData(
            source="test",
            data_type="news",
            content={"title": "测试新闻"},
            metadata={"url": "http://test.com"}
        )

        assert data.source == "test"
        assert data.data_type == "news"
        assert data.content["title"] == "测试新闻"
        assert data.error is None

    def test_collected_data_with_error(self):
        """测试带错误的采集数据"""
        data = CollectedData(
            source="test",
            data_type="news",
            content=None,
            error="连接失败"
        )

        assert data.error == "连接失败"
        assert data.content is None

    def test_to_dict(self):
        """测试转换为字典"""
        data = CollectedData(
            source="akshare",
            data_type="realtime",
            content={"price": 100}
        )

        result = data.to_dict()

        assert result["source"] == "akshare"
        assert result["data_type"] == "realtime"
        assert result["content"]["price"] == 100
        assert "collected_at" in result


class TestBochaWebCollector:
    """测试博查采集器"""

    def test_collector_init(self):
        """测试采集器初始化"""
        collector = BochaWebCollector()

        assert collector.name == "bocha"
        assert collector.description == "博查AI网页搜索采集"

    def test_is_available_without_key(self):
        """测试无API Key时不可用"""
        # 临时移除环境变量
        original_key = os.environ.get("BOCHA_API_KEY", "")
        os.environ["BOCHA_API_KEY"] = ""

        collector = BochaWebCollector()
        assert not collector.is_available()

        # 恢复环境变量
        if original_key:
            os.environ["BOCHA_API_KEY"] = original_key

    def test_is_available_with_key(self):
        """测试有API Key时可用"""
        os.environ["BOCHA_API_KEY"] = "test_key"

        collector = BochaWebCollector()
        assert collector.is_available()

    @pytest.mark.asyncio
    async def test_collect_without_api_key(self):
        """测试无API Key时的采集"""
        os.environ["BOCHA_API_KEY"] = ""

        collector = BochaWebCollector()
        result = await collector.collect("格力电器")

        assert result.error is not None
        assert "API Key未配置" in result.error

    @pytest.mark.asyncio
    async def test_summarize_results(self):
        """测试结果摘要"""
        collector = BochaWebCollector()

        items = [
            {"title": "新闻1", "snippet": "摘要内容1"},
            {"title": "新闻2", "snippet": "摘要内容2"},
        ]

        summary = collector._summarize_results(items)
        assert "摘要内容1" in summary

        # 空结果测试
        empty_summary = collector._summarize_results([])
        assert empty_summary == "无相关信息"


class TestAkshareCollector:
    """测试Akshare采集器"""

    def test_collector_init(self):
        """测试采集器初始化"""
        collector = AkshareCollector()

        assert collector.name == "akshare"
        assert collector.description == "Akshare金融数据采集"

    def test_stock_code_mapping(self):
        """测试股票代码映射"""
        collector = AkshareCollector()

        # 测试已知股票
        assert collector._get_stock_code("格力") == "000651"
        assert collector._get_stock_code("格力电器") == "000651"
        assert collector._get_stock_code("茅台") == "600519"
        assert collector._get_stock_code("比亚迪") == "002594"

        # 测试部分匹配
        assert collector._get_stock_code("格力电器股份有限公司") == "000651"

        # 测试未知股票
        assert collector._get_stock_code("未知股票XYZ") is None

        # 测试直接代码
        assert collector._get_stock_code("000001") == "000001"

    @pytest.mark.asyncio
    async def test_collect_unknown_stock(self):
        """测试未知股票采集"""
        collector = AkshareCollector()

        # 如果akshare未安装
        if not collector.is_available():
            result = await collector.collect("未知股票XYZ")
            assert result.error is not None
            assert "akshare未安装" in result.error
        else:
            # akshare可用，测试未知股票
            result = await collector.collect("完全不存在的股票名称")
            assert result.error is not None or result.content.get("error") is not None

    @pytest.mark.asyncio
    async def test_collect_with_code(self):
        """测试用代码直接采集"""
        collector = AkshareCollector()

        if not collector.is_available():
            pytest.skip("akshare未安装")

        # 测试用代码采集
        result = await collector.collect("000651", data_type="realtime")

        # 结果应该包含股票信息（可能成功也可能失败，取决于网络）
        assert result.source == "akshare"
        assert result.data_type == "realtime"


class TestDataCollectorManager:
    """测试采集管理器"""

    def test_manager_init(self):
        """测试管理器初始化"""
        manager = DataCollectorManager()

        assert "bocha" in manager.collectors
        assert "akshare" in manager.collectors

    def test_list_collectors(self):
        """测试列出采集器"""
        manager = DataCollectorManager()
        collectors = manager.list_collectors()

        assert len(collectors) == 2
        assert any(c["name"] == "bocha" for c in collectors)
        assert any(c["name"] == "akshare" for c in collectors)

    def test_get_collector(self):
        """测试获取采集器"""
        manager = DataCollectorManager()

        bocha = manager.get_collector("bocha")
        assert bocha is not None
        assert bocha.name == "bocha"

        unknown = manager.get_collector("unknown")
        assert unknown is None

    @pytest.mark.asyncio
    async def test_collect_all(self):
        """测试使用所有采集器采集"""
        manager = DataCollectorManager()

        results = await manager.collect_all("格力电器")

        assert "bocha" in results
        assert "akshare" in results

        # 检查结果结构
        for name, data in results.items():
            assert isinstance(data, CollectedData)
            assert data.source == name

    @pytest.mark.asyncio
    async def test_collect_for_stock(self):
        """测试股票综合数据采集"""
        manager = DataCollectorManager()

        summary = await manager.collect_for_stock("格力")

        assert summary["stock_name"] == "格力"
        assert "collected_at" in summary
        # stock_data和news可能为None（取决于采集器可用性）


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_collection_flow(self):
        """测试完整采集流程"""
        manager = DataCollectorManager()

        # 模拟会议采集场景
        stock_name = "格力电器"

        # 1. 列出可用采集器
        collectors = manager.list_collectors()
        available = [c for c in collectors if c["available"]]

        # 2. 执行采集
        if any(c["name"] == "akshare" for c in available):
            akshare_result = await manager.collectors["akshare"].collect(stock_name)
            assert akshare_result.source == "akshare"

        # 3. 采集新闻
        if any(c["name"] == "bocha" for c in available):
            bocha_result = await manager.collectors["bocha"].collect(
                f"{stock_name} 最新动态",
                data_type="news"
            )
            assert bocha_result.source == "bocha"

    @pytest.mark.asyncio
    async def test_batch_collection(self):
        """测试批量采集"""
        collector = AkshareCollector()

        if not collector.is_available():
            pytest.skip("akshare未安装")

        stocks = ["格力", "茅台", "比亚迪"]
        results = await collector.collect_batch(stocks, data_type="realtime")

        assert len(results) == 3
        for result in results:
            assert isinstance(result, CollectedData)


# 运行测试的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])