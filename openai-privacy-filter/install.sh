#!/bin/bash
# OpenAI Privacy Filter 安装脚本
# 使用系统 Python 在本地创建虚拟环境

echo "=========================================="
echo "OpenAI Privacy Filter 安装脚本"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "部署目录：$SCRIPT_DIR"

# 1. 使用系统 Python 创建虚拟环境
echo -e "\n[1/4] 使用系统 Python 创建虚拟环境..."
/usr/bin/python3 -m venv venv
source venv/bin/activate

# 2. 升级 pip
echo -e "\n[2/4] 升级 pip..."
pip install --upgrade pip

# 3. 安装依赖
echo -e "\n[3/4] 安装 Python 依赖包..."
pip install transformers torch accelerate sentencepiece

# 4. 验证安装
echo -e "\n[4/4] 验证安装..."
python -c "from transformers import pipeline; print('✓ Transformers 安装成功')"
python -c "import torch; print(f'✓ PyTorch 版本：{torch.__version__}')"

echo -e "\n=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "使用方法："
echo "  1. 进入目录：cd $SCRIPT_DIR"
echo "  2. 激活虚拟环境：source venv/bin/activate"
echo "  3. 运行示例脚本：python privacy_filter_demo.py"
echo ""
echo "模型信息："
echo "  - 模型名称：openai/privacy-filter"
echo "  - 参数量：1.5B (MoE, 激活 50M)"
echo "  - 上下文：128K tokens"
echo "  - 许可证：Apache 2.0"
echo "  - Hugging Face: https://huggingface.co/openai/privacy-filter"
echo ""
