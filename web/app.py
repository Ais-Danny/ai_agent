import os
from flask import Flask
from .utils import recursion_logger
from .routes import main_bp

# 初始化Flask应用
app = Flask(__name__)

# 配置应用
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'

# 确保数据目录存在
def ensure_directories():
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./data/memory', exist_ok=True)

# 注册蓝图
app.register_blueprint(main_bp)

if __name__ == '__main__':
    ensure_directories()
    print("\n=== AI 智能体网页界面 ===")
    print("正在启动Web服务器...")
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
