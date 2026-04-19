"""
Advisor Registry - 顾问注册表

管理所有10位投资顾问的注册和查询
"""

from typing import Dict, List, Optional, Type
from .base import BaseAdvisor, AdvisorType, AdvisorPersonality
from .advisors import (
    BenjaminGrahamAdvisor,
    WarrenBuffettAdvisor,
    CharlieMungerAdvisor,
    PeterLynchAdvisor,
    ZhangKunAdvisor,
    WangChenAdvisor,
    SteveNisonAdvisor,
    EdwinLefevreAdvisor,
    LinJunruiAdvisor,
    PrivateEquityAdvisor
)


class AdvisorRegistry:
    """顾问注册表"""

    _advisors: Dict[str, BaseAdvisor] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """初始化所有顾问"""
        if cls._initialized:
            return

        # 注册10位顾问
        advisors_list = [
            BenjaminGrahamAdvisor(),
            WarrenBuffettAdvisor(),
            CharlieMungerAdvisor(),
            PeterLynchAdvisor(),
            ZhangKunAdvisor(),
            WangChenAdvisor(),
            SteveNisonAdvisor(),
            EdwinLefevreAdvisor(),
            LinJunruiAdvisor(),
            PrivateEquityAdvisor()
        ]

        for advisor in advisors_list:
            cls._advisors[advisor.personality.name] = advisor

        cls._initialized = True

    @classmethod
    def get_advisor(cls, name: str) -> Optional[BaseAdvisor]:
        """获取指定顾问（支持部分名称匹配）"""
        cls.initialize()

        # 先尝试精确匹配
        if name in cls._advisors:
            return cls._advisors[name]

        # 尝试部分匹配（提取核心名称）
        # 处理格式如: "沃伦·巴菲特（价值派）- 评估..."
        core_name = name.split('（')[0].split('(')[0].split('-')[0].strip()
        if core_name in cls._advisors:
            return cls._advisors[core_name]

        # 尝试包含匹配
        for registered_name, advisor in cls._advisors.items():
            if registered_name in name or name in registered_name:
                return advisor

        return None

    @classmethod
    def get_all_advisors(cls) -> List[BaseAdvisor]:
        """获取所有顾问"""
        cls.initialize()
        return list(cls._advisors.values())

    @classmethod
    def get_advisors_by_type(cls, type: AdvisorType) -> List[BaseAdvisor]:
        """按类型获取顾问"""
        cls.initialize()
        return [a for a in cls._advisors.values()
                if a.personality.type == type]

    @classmethod
    def get_tension_pairs(cls) -> List[Dict[str, str]]:
        """获取张力对组合"""
        cls.initialize()
        pairs = []

        # 预定义的张力对
        predefined_pairs = [
            ("本杰明·格雷厄姆", "史蒂夫·尼森"),  # 价值 vs 技术
            ("沃伦·巴菲特", "林君叡"),           # 长期持有 vs 风险投资
            ("王琛", "埃德温·勒菲弗"),           # 量化理性 vs 人性心理
            ("张坤", "彼得·林奇"),               # 消费深度 vs 广泛选股
            ("查理·芒格", "史蒂夫·尼森"),       # 多学科思维 vs 技术派
        ]

        for name1, name2 in predefined_pairs:
            if name1 in cls._advisors and name2 in cls._advisors:
                pairs.append({
                    "advisor1": name1,
                    "advisor2": name2,
                    "tension": cls._describe_tension(name1, name2)
                })

        return pairs

    @classmethod
    def _describe_tension(cls, name1: str, name2: str) -> str:
        """描述张力对的对立关系"""
        tension_descriptions = {
            ("本杰明·格雷厄姆", "史蒂夫·尼森"): "价值派注重安全边际和内在价值，技术派关注价格形态和市场信号",
            ("沃伦·巴菲特", "林君叡"): "长期价值投资追求确定性，风险投资拥抱不确定性和成长潜力",
            ("王琛", "埃德温·勒菲弗"): "量化模型追求理性数据驱动，交易心理学洞察人性弱点",
            ("张坤", "彼得·林奇"): "深度研究少数优质标的，广泛探索发现十倍股机会",
            ("查理·芒格", "史蒂夫·尼森"): "多学科理性思维框架，K线形态直觉判断",
        }
        return tension_descriptions.get((name1, name2), "观点碰撞")

    @classmethod
    def select_advisors_for_topic(cls, topic: str, topic_type: str) -> List[str]:
        """
        根据议题选择合适的顾问组合

        Args:
            topic: 议题内容
            topic_type: 议题类型

        Returns:
            List[str]: 选择的顾问名单
        """
        cls.initialize()

        # 根据议题类型选择核心顾问
        selected = []

        if topic_type in ["估值分析", "价值投资", "基本面分析"]:
            # 价值投资相关
            selected.extend([
                "本杰明·格雷厄姆",
                "沃伦·巴菲特",
                "查理·芒格"
            ])
        elif topic_type in ["技术分析", "趋势判断"]:
            # 技术分析相关
            selected.extend([
                "史蒂夫·尼森",
                "埃德温·勒菲弗"
            ])
        elif topic_type in ["成长投资", "新兴行业"]:
            # 成长投资相关
            selected.extend([
                "彼得·林奇",
                "林君叡"
            ])
        elif topic_type in ["量化分析", "数据驱动"]:
            # 量化相关
            selected.extend([
                "王琛",
                "查理·芒格"
            ])
        else:
            # 综合分析 - 选择代表性顾问
            selected.extend([
                "沃伦·巴菲特",
                "查理·芒格",
                "彼得·林奇"
            ])

        # 补充中国视角
        if "A股" in topic or "中国" in topic or any(c in topic for c in "格力茅台平安腾讯"):
            selected.append("张坤")
            selected.append("顶级私募专家")

        # 补充风险视角
        selected.append("顶级私募专家")

        # 确保张力对存在
        all_names = [a.personality.name for a in cls._advisors.values()]
        for pair in cls.get_tension_pairs():
            if pair["advisor1"] not in selected and pair["advisor2"] not in selected:
                # 补充一个张力对成员
                if pair["advisor1"] in all_names:
                    selected.append(pair["advisor1"])

        # 限制数量5-7位
        if len(selected) > 7:
            selected = selected[:7]

        # 确保都在注册表中
        return [name for name in selected if name in cls._advisors]

    @classmethod
    def get_advisor_info(cls) -> List[Dict]:
        """获取所有顾问信息（用于展示）"""
        cls.initialize()
        return [
            {
                "name": a.personality.name,
                "title": a.personality.title,
                "type": a.personality.type.value,
                "philosophy": a.personality.philosophy,
                "style": a.personality.style,
                "avatar": a.personality.avatar
            }
            for a in cls._advisors.values()
        ]