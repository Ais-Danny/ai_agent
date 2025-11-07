import uuid
import sys
import os
from flask import Blueprint, render_template, request, jsonify, session
from .utils import recursion_logger, load_sessions, load_session_history, save_session_history, delete_session
from functools import wraps

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入Langgraph_Agent
from main import Langgraph_Agent

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 全局智能体实例
agent = None

# 初始化智能体
def init_agent():
    global agent
    # 导入必要的配置和工具
    from src.config.config_model import config
    from src.prompt import system_prompt
    from src.extend.tool import list_files, read_file, write_file, run_cmd
    
    # 初始化环境变量
    config.langsmith_config.init_env()
    
    # 将递归日志器绑定到智能体
    agent = Langgraph_Agent(
        config.llm_model,
        tools=[list_files, read_file, write_file, run_cmd],
        system_prompt=system_prompt
    )
    agent._logger = recursion_logger
    
    # 使用装饰器包装invoke方法以记录递归调用
    if not hasattr(agent.invoke, '_wrapped'):
        from .utils import RecursionLogger
        agent.invoke = RecursionLogger.log_recursion(agent.invoke)

@main_bp.before_request
def before_request():
    """请求前初始化"""
    global agent
    if agent is None:
        init_agent()
    
    # 确保有当前会话ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@main_bp.route('/')
def index():
    """主页路由"""
    sessions = load_sessions()
    current_session = session.get('session_id')
    
    # 检查是否是临时会话
    is_temp_session = current_session and current_session.startswith('新会话_') and 'temp_history' in session
    
    if is_temp_session:
        # 从session中获取临时历史
        history = session.get('temp_history', [])
    else:
        # 从硬盘加载历史
        history = load_session_history(current_session)
    
    return render_template('index.html', 
                          sessions=sessions, 
                          current_session=current_session, 
                          history=history, 
                          recursion_logs=recursion_logger.get_logs())

@main_bp.route('/new_session', methods=['POST'])
def new_session():
    """创建新会话 - 不立即保存到硬盘，只在会话中设置ID"""
    import datetime
    # 使用临时会话ID或生成新ID
    temp_id = request.form.get('temp_session_id')
    if temp_id and temp_id.startswith('新会话_'):
        session['session_id'] = temp_id
    else:
        session['session_id'] = f"新会话_{datetime.now().strftime('%H%M%S')}"
    
    # 清空会话历史，但不保存到硬盘
    session['temp_history'] = []
    
    return index()

@main_bp.route('/switch_session', methods=['POST'])
def switch_session():
    """切换会话"""
    session_id = request.form.get('session_id')
    if session_id and session_id in load_sessions():
        # 检查当前会话是否为空且是临时会话，如果是则删除
        current_session = session.get('session_id')
        if current_session and current_session.startswith('新会话_'):
            current_history = load_session_history(current_session)
            if not current_history or len(current_history) == 0:
                # 删除未使用的临时空会话
                delete_session(current_session)
        
        # 切换到新会话
        session['session_id'] = session_id
    
    return index()

@main_bp.route('/save_session', methods=['POST'])
def save_session():
    """保存当前会话到硬盘"""
    try:
        current_session = session.get('session_id')
        
        # 检查是否是临时会话
        if current_session.startswith('新会话_') and 'temp_history' in session:
            # 从session中获取临时历史
            history = session.get('temp_history', [])
            
            # 如果有历史记录，保存到硬盘
            if history:
                # 可以根据第一条消息自动生成会话标题
                if len(history) >= 2 and history[0][0] == 'user':
                    # 从第一条用户消息提取标题（最多30个字符）
                    first_message = history[0][1][:30].replace('\n', ' ')
                    new_session_id = f"会话_{first_message}"
                    # 保存到新的会话ID
                    save_session_history(new_session_id, history)
                    # 更新session中的ID
                    session['session_id'] = new_session_id
                    # 清除临时历史
                    session.pop('temp_history', None)
                    return jsonify({'message': '会话已保存', 'session_id': new_session_id})
                else:
                    # 直接使用当前临时ID保存
                    save_session_history(current_session, history)
                    # 清除临时历史
                    session.pop('temp_history', None)
                    return jsonify({'message': '会话已保存'})
            else:
                return jsonify({'message': '会话为空，无法保存'}), 400
        else:
            # 非临时会话，直接保存
            history = load_session_history(current_session)
            save_session_history(current_session, history)
            return jsonify({'message': '会话已保存'})
    except Exception as e:
        return jsonify({'message': f'保存失败: {str(e)}'}), 500

@main_bp.route('/send_message', methods=['POST'])
def send_message():
    """发送消息并获取回复"""
    try:
        message = request.form.get('message', '')
        current_session = session.get('session_id')
        
        # 检查是否是临时会话（尚未保存到硬盘）
        is_temp_session = current_session.startswith('新会话_') and 'temp_history' in session
        
        if is_temp_session:
            # 从session中获取临时历史
            history = session.get('temp_history', [])
        else:
            # 从硬盘加载历史
            history = load_session_history(current_session)
        
        # 添加用户消息到历史
        history.append(['user', message])
        
        # 获取智能体回复
        response = agent.invoke(message)
        
        # 处理OpenAIMessage对象，确保返回可序列化的内容
        if hasattr(response, 'content'):
            response_text = response.content
        elif hasattr(response, 'text'):
            response_text = response.text
        elif isinstance(response, str):
            response_text = response
        else:
            response_text = str(response)
        
        # 添加智能体回复到历史
        history.append(['assistant', response_text])
        
        # 更新临时会话历史或保存到硬盘
        if is_temp_session:
            session['temp_history'] = history
        else:
            save_session_history(current_session, history)
        
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'response': f'发生错误: {str(e)}'}), 500

@main_bp.route('/continue_from_history', methods=['POST'])
def continue_from_history():
    """从历史记录继续对话"""
    try:
        history_index = int(request.form.get('history_index', 0))
        current_session = session.get('session_id')
        
        # 检查是否是临时会话
        is_temp_session = current_session.startswith('新会话_') and 'temp_history' in session
        
        if is_temp_session:
            # 从session中获取临时历史
            history = session.get('temp_history', [])
        else:
            # 从硬盘加载历史
            history = load_session_history(current_session)
        
        # 截取历史记录到指定索引
        if history_index < len(history):
            history = history[:history_index + 1]
            
            # 更新临时会话历史或保存到硬盘
            if is_temp_session:
                session['temp_history'] = history
            else:
                save_session_history(current_session, history)
        
        return index()
    except Exception as e:
        return jsonify({'message': f'操作失败: {str(e)}'}), 500

@main_bp.route('/get_recursion_logs', methods=['GET'])
def get_recursion_logs():
    """获取递归调用日志"""
    return jsonify(recursion_logger.get_logs())

@main_bp.route('/delete_session', methods=['POST'])
def delete_session_route():
    """删除指定会话"""
    try:
        session_id = request.form.get('session_id')
        current_session = session.get('session_id')
        
        # 不能删除当前正在使用的会话
        if session_id == current_session:
            return jsonify({'success': False, 'message': '不能删除当前正在使用的会话'}), 400
        
        # 执行删除
        if delete_session(session_id):
            return jsonify({'success': True, 'message': '会话删除成功'})
        else:
            return jsonify({'success': False, 'message': '会话不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@main_bp.route('/rename_session', methods=['POST'])
def rename_session():
    """重命名会话"""
    try:
        old_session_id = request.form.get('old_name')
        new_session_name = request.form.get('new_name')
        
        # 验证输入
        if not old_session_id or not new_session_name:
            return jsonify({'success': False, 'message': '会话ID和新名称不能为空'}), 400
        
        # 确保新名称是有效的文件名
        new_session_name = new_session_name.replace('/', '').replace('\\', '')
        
        current_session = session.get('session_id')
        
        # 检查是否是临时会话的重命名
        if old_session_id == current_session and current_session.startswith('新会话_') and 'temp_history' in session:
            # 直接更新session中的ID
            session['session_id'] = new_session_name
            return jsonify({'success': True, 'message': '会话重命名成功', 'new_session_id': new_session_name})
        else:
            # 常规会话重命名
            # 加载旧会话历史
            old_history = load_session_history(old_session_id)
            if not old_history:
                return jsonify({'success': False, 'message': '旧会话不存在'}), 404
            
            # 保存为新会话
            save_session_history(new_session_name, old_history)
            
            # 删除旧会话
            delete_session(old_session_id)
            
            # 如果是当前会话，更新session中的ID
            if old_session_id == current_session:
                session['session_id'] = new_session_name
            
            return jsonify({'success': True, 'message': '会话重命名成功', 'new_session_id': new_session_name})
    except Exception as e:
        return jsonify({'success': False, 'message': f'重命名失败: {str(e)}'}), 500
