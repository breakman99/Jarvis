#!/bin/bash
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
echo "环境已准备好！"