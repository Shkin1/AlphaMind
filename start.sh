#!/bin/bash
# AlphaMind 投研会启动脚本

echo "========================================"
echo "  AlphaMind 投研会"
echo "  AI投资专家圆桌会议系统"
echo "========================================"

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python"
    exit 1
fi

# 进入后端目录
cd backend

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "提示: 未找到 .env 文件"
    echo "请复制 .env.example 并填入你的 OPENAI_API_KEY"
    cp .env.example .env
    echo ".env 文件已创建，请编辑并填入 API Key"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
pip install -r requirements.txt -q

# 启动服务
echo "启动服务..."
echo "访问地址: http://localhost:8000"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000