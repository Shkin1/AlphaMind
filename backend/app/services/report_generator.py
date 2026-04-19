"""
Report Generator - HTML报告生成器

生成交互式HTML可视化报告
"""

from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime


class ReportGenerator:
    """HTML报告生成器"""

    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_report(self, meeting_state: Dict) -> str:
        """
        生成HTML报告

        Args:
            meeting_state: 会议状态数据

        Returns:
            str: HTML内容
        """
        template = self.env.get_template('report.html')

        # 构建报告数据
        report_data = {
            "meeting_id": meeting_state.get("meeting_id", ""),
            "topic": meeting_state.get("topic", ""),
            "topic_type": meeting_state.get("topic_type", "综合分析"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stock_data": meeting_state.get("stock_data", {}),

            # Phase 0
            "restated_topic": meeting_state.get("restated_topic", meeting_state.get("topic", "")),
            "key_info": meeting_state.get("key_info", {}),

            # Phase 1
            "questions": meeting_state.get("clarification_questions", []),
            "user_answers": meeting_state.get("user_answers", {}),

            # Phase 2
            "advisors": meeting_state.get("selected_advisors", []),
            "tension_pairs": meeting_state.get("tension_pairs", []),

            # Phase 3
            "opinions": meeting_state.get("opinions", []),

            # Phase 4
            "crossfire_dialogs": meeting_state.get("crossfire_dialogs", []),

            # Phase 5
            "resolution": meeting_state.get("resolution", {}),
        }

        return template.render(**report_data)

    def save_report(self, meeting_state: Dict, output_dir: str = None) -> str:
        """
        保存HTML报告到文件

        Args:
            meeting_state: 会议状态数据
            output_dir: 输出目录

        Returns:
            str: 文件路径
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')

        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 生成报告
        html_content = self.generate_report(meeting_state)

        # 文件名
        meeting_id = meeting_state.get("meeting_id", "unknown")
        filename = f"report_{meeting_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(output_dir, filename)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filepath


# 创建全局实例
report_generator = ReportGenerator()