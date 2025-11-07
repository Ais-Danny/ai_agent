import json
import os
from datetime import datetime
from functools import wraps

class RecursionLogger:
    """递归调用日志记录器"""
    def __init__(self):
        self.logs = []
    
    def log(self, level, function, params=None, result=None):
        """记录日志"""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
            'level': level,
            'function': function,
            'params': params,
            'result': result
        }
        self.logs.append(log_entry)
        # 限制日志数量，避免内存溢出
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
    
    def get_logs(self):
        """获取所有日志"""
        return self.logs
    
    def clear_logs(self):
        """清空日志"""
        self.logs = []
    
    def log_recursion(func):
        """递归调用装饰器"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 记录开始日志
            if hasattr(self, '_logger'):
                params = kwargs.copy()
                params['args'] = [str(arg) for arg in args[:1]]  # 只记录第一个参数（通常是prompt）
                self._logger.log('START', func.__name__, params=params)
            
            try:
                # 执行函数
                result = func(self, *args, **kwargs)
                
                # 记录结束日志
                if hasattr(self, '_logger'):
                    # 只记录结果的简要信息
                    result_summary = str(result)[:200] + ('...' if len(str(result)) > 200 else '')
                    self._logger.log('END', func.__name__, result=result_summary)
                
                return result
            except Exception as e:
                # 记录错误日志
                if hasattr(self, '_logger'):
                    self._logger.log('ERROR', func.__name__, result=str(e))
                raise
        return wrapper

def load_sessions():
    """加载所有会话列表"""
    memory_dir = './data/memory'
    sessions = []
    if os.path.exists(memory_dir):
        for filename in os.listdir(memory_dir):
            if filename.endswith('.json'):
                sessions.append(filename[:-5])  # 移除.json后缀
    return sessions

def load_session_history(session_id):
    """加载指定会话历史"""
    file_path = f'./data/memory/{session_id}.json'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_session_history(session_id, history):
    """保存会话历史"""
    file_path = f'./data/memory/{session_id}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def delete_session(session_id):
    """删除会话"""
    file_path = f'./data/memory/{session_id}.json'
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

# 创建全局递归日志器实例
recursion_logger = RecursionLogger()
