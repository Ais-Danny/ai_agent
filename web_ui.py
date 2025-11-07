from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import json
from pathlib import Path
import uuid
import threading
import time
import logging
from datetime import datetime

# 导入现有的智能体和记忆管理模块
from src.config.config_model import config
from src.entity.agent.langgraph_agent import Langgraph_Agent
from src.prompt import system_prompt
from src.extend.tool import list_files, read_file, write_file, run_cmd

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 初始化环境变量
config.langsmith_config.init_env()

# 创建智能体实例
agent = Langgraph_Agent(
    config.llm_model,
    tools=[list_files, read_file, write_file, run_cmd],
    system_prompt=system_prompt
)

# 递归过程记录器
class RecursionLogger:
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RecursionLogger, cls).__new__(cls)
                cls._instance.logs = []
                cls._instance.session_logs = {}
        return cls._instance
    
    def add_log(self, session_id, level, function, params=None, result=None):
        """添加递归调用日志"""
        with self._lock:
            if session_id not in self.session_logs:
                self.session_logs[session_id] = []
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'function': function,
                'params': params or {},
                'result': result
            }
            self.session_logs[session_id].append(log_entry)
    
    def get_logs(self, session_id):
        """获取指定会话的递归日志"""
        with self._lock:
            return self.session_logs.get(session_id, [])
    
    def clear_logs(self, session_id):
        """清空指定会话的递归日志"""
        with self._lock:
            if session_id in self.session_logs:
                self.session_logs[session_id] = []

recursion_logger = RecursionLogger()

# 扩展Langgraph_Agent的invoke方法以记录递归过程
original_invoke = agent.__class__.invoke

def wrapped_invoke(self, user_input, thread_id="1", max_steps=None, stream_func=None):
    # 创建原始stream_func的包装器
    original_stream_func = stream_func
    
    def wrapped_stream_func(role, content):
        recursion_logger.add_log(
            thread_id,
            'INFO',
            'stream_response',
            {'role': role},
            {'content': content[:100] + '...' if len(content) > 100 else content}
        )
        if original_stream_func:
            original_stream_func(role, content)
    
    try:
        recursion_logger.add_log(
            thread_id,
            'START',
            'agent_invoke',
            {'user_input': user_input, 'max_steps': max_steps},
            None
        )
        
        result = original_invoke(self, user_input, thread_id, max_steps, wrapped_stream_func)
        
        recursion_logger.add_log(
            thread_id,
            'END',
            'agent_invoke',
            None,
            {'status': 'success', 'result_type': type(result).__name__}
        )
        
        return result
    except Exception as e:
        recursion_logger.add_log(
            thread_id,
            'ERROR',
            'agent_invoke',
            None,
            {'status': 'error', 'message': str(e)}
        )
        raise

# 替换原始方法
agent.__class__.invoke = wrapped_invoke

# 创建必要的目录
DATA_DIR = Path("./data")
MEMORY_DIR = DATA_DIR / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    # 获取或创建会话ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())[:8]
    
    # 获取所有可用的会话
    sessions = get_all_sessions()
    
    # 获取当前会话的历史记录
    current_session_id = session['session_id']
    history = get_session_history(current_session_id)
    
    # 获取递归日志
    recursion_logs = recursion_logger.get_logs(current_session_id)
    
    return render_template('index.html', 
                          current_session=current_session_id, 
                          sessions=sessions,
                          history=history,
                          recursion_logs=recursion_logs)

def get_all_sessions():
    """获取所有可用的会话列表"""
    sessions = []
    for file in MEMORY_DIR.glob("*.json"):
        session_id = file.stem
        sessions.append(session_id)
    # 添加内存中的会话
    for thread_id in agent.memory.list_threads():
        if thread_id not in sessions:
            sessions.append(thread_id)
    return sessions

def get_session_history(session_id):
    """获取指定会话的历史记录"""
    try:
        # 尝试从文件加载
        history_file = MEMORY_DIR / f"{session_id}.json"
        if history_file.exists():
            return json.loads(history_file.read_text(encoding="utf-8"))
        # 尝试从内存获取
        return agent.memory.get_history(session_id)
    except Exception as e:
        logger.error(f"获取会话历史失败: {e}")
        return []

@app.route('/new_session', methods=['POST'])
def new_session():
    """创建新会话"""
    session['session_id'] = str(uuid.uuid4())[:8]
    recursion_logger.clear_logs(session['session_id'])
    return redirect(url_for('index'))

@app.route('/switch_session', methods=['POST'])
def switch_session():
    """切换会话"""
    new_session_id = request.form.get('session_id')
    if new_session_id:
        session['session_id'] = new_session_id
        # 加载会话历史
        agent.memory.load(new_session_id)
    return redirect(url_for('index'))

@app.route('/save_session', methods=['POST'])
def save_session():
    """保存当前会话"""
    current_session_id = session.get('session_id')
    if current_session_id:
        try:
            agent.memory.save(current_session_id)
            return jsonify({'status': 'success', 'message': '会话保存成功'})
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': '无活动会话'})

@app.route('/continue_from_history', methods=['POST'])
def continue_from_history():
    """从历史记录中的某一点继续对话"""
    current_session_id = session.get('session_id')
    history_index = int(request.form.get('history_index', 0))
    
    if current_session_id:
        try:
            # 获取完整历史
            full_history = get_session_history(current_session_id)
            if 0 <= history_index < len(full_history):
                # 截取历史记录
                new_history = full_history[:history_index + 1]
                # 创建新的会话ID
                new_session_id = f"{current_session_id}_continue_{str(uuid.uuid4())[:4]}"
                # 保存新会话
                (MEMORY_DIR / f"{new_session_id}.json").write_text(
                    json.dumps(new_history, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                # 切换到新会话
                session['session_id'] = new_session_id
                agent.memory.load(new_session_id)
                recursion_logger.clear_logs(new_session_id)
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"从历史继续失败: {e}")
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    """发送消息到智能体"""
    current_session_id = session.get('session_id')
    user_message = request.form.get('message', '').strip()
    
    if not user_message or not current_session_id:
        return jsonify({'status': 'error', 'message': '消息不能为空'})
    
    # 记录用户消息
    agent.memory.add_message(current_session_id, 'user', user_message)
    
    # 调用智能体
    try:
        # 记录递归开始
        recursion_logger.clear_logs(current_session_id)
        
        # 调用智能体
        result = agent.invoke(user_message, thread_id=current_session_id)
        
        # 保存会话
        agent.memory.save(current_session_id)
        
        return jsonify({
            'status': 'success',
            'response': result.last_message if hasattr(result, 'last_message') else str(result)
        })
    except Exception as e:
        logger.error(f"调用智能体失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_recursion_logs')
def get_recursion_logs():
    """获取递归调用日志"""
    current_session_id = session.get('session_id')
    logs = recursion_logger.get_logs(current_session_id)
    return jsonify(logs)

# 创建templates目录
os.makedirs('templates', exist_ok=True)

# 创建index.html模板
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 智能体对话系统</title>
    <!-- 添加Markdown渲染库 -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- 添加代码高亮库 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            display: grid;
            grid-template-columns: 250px 1fr 300px;
            grid-template-rows: 60px 1fr auto;
            grid-template-areas: 
                "header header header"
                "sidebar chat recursion"
                "footer footer footer";
            height: 100vh;
            gap: 1px;
            background-color: #ddd;
        }
        
        .header {
            grid-area: header;
            background-color: #2c3e50;
            color: white;
            padding: 0 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 20px;
            font-weight: 500;
        }
        
        .header .actions {
            display: flex;
            gap: 10px;
        }
        
        .header button {
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .header button:hover {
            background-color: #2980b9;
        }
        
        .sidebar {
            grid-area: sidebar;
            background-color: white;
            padding: 15px;
            overflow-y: auto;
            border-right: 1px solid #ddd;
        }
        
        .sidebar h3 {
            font-size: 16px;
            margin-bottom: 15px;
            color: #2c3e50;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .session-list {
            list-style: none;
        }
        
        .session-item {
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session-item:hover {
            background-color: #f0f0f0;
        }
        
        .session-item.active {
            background-color: #e3f2fd;
            border-left: 3px solid #2196f3;
        }
        
        .session-item .session-id {
            font-weight: 500;
            font-size: 14px;
        }
        
        .session-item .time {
            font-size: 12px;
            color: #888;
        }
        
        .chat-container {
            grid-area: chat;
            background-color: white;
            display: flex;
            flex-direction: column;
        }
        
        .chat-history {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 12px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .message.user {
            background-color: #dcf8c6;
            margin-left: auto;
            position: relative;
        }
        
        .message.user::before {
            content: '';
            position: absolute;
            top: 15px;
            right: -10px;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
            border-left: 10px solid #dcf8c6;
        }
        
        .message.assistant {
            background-color: #f0f0f0;
            margin-right: auto;
            position: relative;
        }
        
        .message.assistant::before {
            content: '';
            position: absolute;
            top: 15px;
            left: -10px;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
            border-right: 10px solid #f0f0f0;
        }
        
        .message.system {
            background-color: #e3f2fd;
            margin: 0 auto;
            text-align: center;
            font-style: italic;
            font-size: 14px;
        }
        
        .chat-input {
            padding: 20px;
            background-color: #fafafa;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        
        .chat-input input:focus {
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }
        
        .chat-input button {
            padding: 12px 25px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
        }
        
        .chat-input button:hover {
            background-color: #2980b9;
        }
        
        .recursion-container {
            grid-area: recursion;
            background-color: white;
            border-left: 1px solid #ddd;
            display: flex;
            flex-direction: column;
        }
        
        .recursion-header {
            padding: 15px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .recursion-header h3 {
            font-size: 16px;
            color: #2c3e50;
        }
        
        .recursion-header button {
            padding: 5px 10px;
            background-color: #dc3545;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .recursion-header button:hover {
            background-color: #c82333;
        }
        
        .recursion-logs {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
        }
        
        .recursion-log {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 4px;
            background-color: #f8f9fa;
            border-left: 3px solid #6c757d;
        }
        
        .recursion-log.START {
            border-left-color: #28a745;
            background-color: #d4edda;
        }
        
        .recursion-log.END {
            border-left-color: #17a2b8;
            background-color: #d1ecf1;
        }
        
        .recursion-log.ERROR {
            border-left-color: #dc3545;
            background-color: #f8d7da;
        }
        
        .recursion-log .timestamp {
            font-size: 11px;
            color: #6c757d;
            margin-bottom: 5px;
        }
        
        .recursion-log .function {
            font-weight: 500;
            color: #495057;
            margin-bottom: 5px;
        }
        
        .recursion-log .params, .recursion-log .result {
            font-size: 12px;
            color: #212529;
        }
        
        .footer {
            grid-area: footer;
            background-color: #343a40;
            color: white;
            padding: 10px 20px;
            font-size: 14px;
            text-align: center;
        }
        
        .history-control {
            position: absolute;
            top: 10px;
            left: 10px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .message:hover .history-control {
            opacity: 1;
        }
        
        .continue-button {
            padding: 3px 8px;
            background-color: #ffc107;
            color: #212529;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .continue-button:hover {
            background-color: #e0a800;
        }
        
        /* Markdown样式增强 */
        .message-content {
            line-height: 1.6;
        }
        
        /* Markdown内容样式 */
        .message-content h1, .message-content h2, .message-content h3, 
        .message-content h4, .message-content h5, .message-content h6 {
            margin-top: 1em;
            margin-bottom: 0.5em;
            font-weight: 600;
            line-height: 1.25;
        }
        
        .message-content h1 { font-size: 1.8em; }
        .message-content h2 { font-size: 1.5em; }
        .message-content h3 { font-size: 1.3em; }
        
        .message-content p {
            margin-bottom: 1em;
        }
        
        .message-content a {
            color: #1a73e8;
            text-decoration: none;
        }
        
        .message-content a:hover {
            text-decoration: underline;
        }
        
        .message-content code {
            background-color: rgba(175, 184, 193, 0.2);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }
        
        .message-content pre {
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 1em;
            overflow-x: auto;
            margin-bottom: 1em;
        }
        
        .message-content pre code {
            background-color: transparent;
            padding: 0;
            border-radius: 0;
        }
        
        .message-content blockquote {
            border-left: 4px solid #dfe2e5;
            padding-left: 1em;
            color: #6a737d;
            margin: 1em 0;
        }
        
        .message-content ul, .message-content ol {
            padding-left: 2em;
            margin: 1em 0;
        }
        
        .message-content li {
            margin-bottom: 0.5em;
        }
        
        .message-content table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        
        .message-content th, .message-content td {
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
            text-align: left;
        }
        
        .message-content th {
            background-color: #f6f8fa;
        }
        
        /* 代码高亮主题适配 */
        .message-content pre code {
            background: none;
            color: inherit;
            font-size: 0.9em;
        }
        
        /* 深色模式代码块适配 */
        .message.assistant .message-content pre {
            background-color: #2d2d2d;
            color: #f8f8f2;
        }
        
        /* 响应式调整 */
        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 200px 1fr 250px;
            }
        }
        
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
                grid-template-rows: 60px auto 1fr auto;
                grid-template-areas: 
                    "header"
                    "sidebar"
                    "chat"
                    "footer";
            }
            
            .recursion-container {
                display: none;
            }
            
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>AI 智能体对话系统</h1>
            <div class="actions">
                <button id="save-btn">保存会话</button>
                <button id="new-btn">新建会话</button>
            </div>
        </header>
        
        <aside class="sidebar">
            <h3>会话列表</h3>
            <ul class="session-list">
                {% for sess in sessions %}
                <li class="session-item {{ 'active' if sess == current_session else '' }}">
                    <span class="session-id">{{ sess }}</span>
                    <span class="time">{{ '当前' if sess == current_session else '' }}</span>
                </li>
                {% endfor %}
            </ul>
        </aside>
        
        <main class="chat-container">
            <div class="chat-history" id="chat-history">
                {% for role, content in history %}
                <div class="message {{ role }}">
                    <div class="history-control">
                        <button class="continue-button" data-index="{{ loop.index0 }}">从此处继续</button>
                    </div>
                    {% if role == 'assistant' %}
                    <div class="message-content markdown-content">{{ content }}</div>
                    {% else %}
                    <div class="message-content">{{ content }}</div>
                    {% endif %}
                </div>
                {% else %}
                <div class="message system">欢迎使用AI智能体对话系统，请输入您的问题...</div>
                {% endfor %}
            </div>
            
            <form class="chat-input" id="chat-form">
                <input type="text" id="message-input" placeholder="请输入您的问题..." autocomplete="off">
                <button type="submit">发送</button>
            </form>
        </main>
        
        <aside class="recursion-container">
            <div class="recursion-header">
                <h3>递归调用过程</h3>
                <button id="clear-logs">清空日志</button>
            </div>
            <div class="recursion-logs" id="recursion-logs">
                {% if recursion_logs %}
                {% for log in recursion_logs %}
                <div class="recursion-log {{ log.level }}">
                    <div class="timestamp">{{ log.timestamp }}</div>
                    <div class="function">{{ log.level }} - {{ log.function }}</div>
                    {% if log.params %}
                    <div class="params">参数: {{ log.params | tojson }}</div>
                    {% endif %}
                    {% if log.result %}
                    <div class="result">结果: {{ log.result | tojson }}</div>
                    {% endif %}
                </div>
                {% endfor %}
                {% else %}
                <div style="text-align: center; color: #999; padding: 20px;">暂无递归调用记录</div>
                {% endif %}
            </div>
        </aside>
        
        <footer class="footer">
            <p>AI智能体对话系统 &copy; 2024</p>
        </footer>
    </div>
    
    <script>
        // 会话切换
        document.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', function() {
                const sessionId = this.querySelector('.session-id').textContent;
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/switch_session';
                form.style.display = 'none';
                
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'session_id';
                input.value = sessionId;
                
                form.appendChild(input);
                document.body.appendChild(form);
                form.submit();
            });
        });
        
        // 新建会话
        document.getElementById('new-btn').addEventListener('click', function() {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/new_session';
            form.style.display = 'none';
            document.body.appendChild(form);
            form.submit();
        });
        
        // 保存会话
        document.getElementById('save-btn').addEventListener('click', function() {
            fetch('/save_session', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                })
                .catch(error => {
                    alert('保存失败');
                });
        });
        
        // 发送消息
        document.getElementById('chat-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const messageInput = document.getElementById('message-input');
            const message = messageInput.value.trim();
            
            if (!message) return;
            
            // 清空输入框
            messageInput.value = '';
            
            // 添加用户消息到界面
            const chatHistory = document.getElementById('chat-history');
            const userMessage = document.createElement('div');
            userMessage.className = 'message user';
            userMessage.innerHTML = `
                <div class="history-control">
                    <button class="continue-button">从此处继续</button>
                </div>
                <div class="message-content">${escapeHtml(message)}</div>
            `;
            chatHistory.appendChild(userMessage);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            
            // 显示加载状态
            const loadingMessage = document.createElement('div');
            loadingMessage.className = 'message assistant';
            loadingMessage.innerHTML = '<div class="message-content">思考中...</div>';
            chatHistory.appendChild(loadingMessage);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            
            // 发送请求
            fetch('/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `message=${encodeURIComponent(message)}`
            })
            .then(response => response.json())
            .then(data => {
                // 移除加载消息
                chatHistory.removeChild(loadingMessage);
                
                // 添加回复消息
                const responseMessage = document.createElement('div');
                responseMessage.className = 'message assistant';
                
                // 渲染Markdown内容
                const markdownContent = marked.parse(data.response);
                
                responseMessage.innerHTML = `
                    <div class="history-control">
                        <button class="continue-button">从此处继续</button>
                    </div>
                    <div class="message-content markdown-content">${markdownContent}</div>
                `;
                
                chatHistory.appendChild(responseMessage);
                
                // 对代码块应用语法高亮
                hljs.highlightAll();
                
                chatHistory.scrollTop = chatHistory.scrollHeight;
                
                // 更新递归日志
                updateRecursionLogs();
            })
            .catch(error => {
                chatHistory.removeChild(loadingMessage);
                const errorMessage = document.createElement('div');
                errorMessage.className = 'message system';
                errorMessage.innerHTML = '<div class="content">发生错误，请重试</div>';
                chatHistory.appendChild(errorMessage);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            });
        });
        
        // 从历史继续
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('continue-button')) {
                const index = e.target.getAttribute('data-index') || 
                            Array.from(document.querySelectorAll('.message')).indexOf(
                                e.target.closest('.message')
                            );
                
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/continue_from_history';
                form.style.display = 'none';
                
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'history_index';
                input.value = index;
                
                form.appendChild(input);
                document.body.appendChild(form);
                form.submit();
            }
        });
        
        // 清空日志
        document.getElementById('clear-logs').addEventListener('click', function() {
            document.getElementById('recursion-logs').innerHTML = 
                '<div style="text-align: center; color: #999; padding: 20px;">暂无递归调用记录</div>';
        });
        
        // 更新递归日志
        function updateRecursionLogs() {
            fetch('/get_recursion_logs')
                .then(response => response.json())
                .then(logs => {
                    const logsContainer = document.getElementById('recursion-logs');
                    if (logs.length > 0) {
                        logsContainer.innerHTML = '';
                        logs.forEach(log => {
                            const logElement = document.createElement('div');
                            logElement.className = `recursion-log ${log.level}`;
                            logElement.innerHTML = `
                                <div class="timestamp">${log.timestamp}</div>
                                <div class="function">${log.level} - ${log.function}</div>
                                ${log.params ? `<div class="params">参数: ${JSON.stringify(log.params)}</div>` : ''}
                                ${log.result ? `<div class="result">结果: ${JSON.stringify(log.result)}</div>` : ''}
                            `;
                            logsContainer.appendChild(logElement);
                        });
                        logsContainer.scrollTop = logsContainer.scrollHeight;
                    }
                });
        }
        
        // HTML转义函数
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
        
        // 页面加载时处理现有的Markdown内容
        document.addEventListener('DOMContentLoaded', function() {
            // 处理所有markdown-content元素
            document.querySelectorAll('.markdown-content').forEach(element => {
                const content = element.textContent;
                const html = marked.parse(content);
                element.innerHTML = html;
            });
            
            // 对代码块应用语法高亮
            hljs.highlightAll();
        });
        
        // 自动滚动到底部
        window.addEventListener('load', function() {
            const chatHistory = document.getElementById('chat-history');
            chatHistory.scrollTop = chatHistory.scrollHeight;
        });
    </script>
</body>
</html>''')

if __name__ == '__main__':
    # 确保data目录存在
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./data/memory', exist_ok=True)
    
    print("\n=== AI 智能体网页界面 ===")
    print("正在启动Web服务器...")
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
