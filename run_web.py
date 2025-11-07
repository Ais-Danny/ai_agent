#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI智能体对话系统 - Web界面启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
