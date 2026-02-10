import json
import os
from datetime import datetime
from functools import wraps
import inspect
import functools
# 尝试导入typing_extensions以确保兼容性
try:
    from typing_extensions import Annotated
except ImportError:
    pass

class RecursionLogger:
    """递归调用日志记录器"""
    def __init__(self):
        self.logs = []
        # 记录工具调用的装饰器
        self.tool_call_decorator = self.log_tool_call
    
    def log(self, level, function, params=None, result=None, source=None, tool_name=None):
        """记录日志"""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
            'level': level,
            'function': function,
            'params': params,
            'result': result,
            'source': source,  # 添加来源对象信息
            'tool_name': tool_name  # 添加工具名称，用于识别工具调用
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
            # 获取对象来源标识
            source = self.__class__.__name__
            if hasattr(self, 'name') and self.name:
                source = self.name
            elif hasattr(self, 'agent_name') and self.agent_name:
                source = self.agent_name
            
            # 确保source不为None
            if source is None:
                source = 'DefaultAgent'
            
            # 记录开始日志
            if hasattr(self, '_logger'):
                params = kwargs.copy()
                params['args'] = [str(arg) for arg in args[:1]]  # 只记录第一个参数（通常是prompt）
                self._logger.log('START', func.__name__, params=params, source=source)
            
            try:
                # 执行函数
                result = func(self, *args, **kwargs)
                
                # 记录结束日志
                if hasattr(self, '_logger'):
                    # 只记录结果的简要信息
                    result_summary = str(result)[:200] + ('...' if len(str(result)) > 200 else '')
                    self._logger.log('END', func.__name__, result=result_summary, source=source)
                
                return result
            except Exception as e:
                # 记录错误日志
                if hasattr(self, '_logger'):
                    self._logger.log('ERROR', func.__name__, result=str(e), source=source)
                raise
        return wrapper
        
    @staticmethod
    def log_tool_call(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取调用来源（通过调用栈分析）
            source = "Unknown"
            try:
                stack = inspect.stack()
                # 查找调用来源
                for frame_info in stack[2:]:
                    if 'self' in frame_info.frame.f_locals:
                        source_obj = frame_info.frame.f_locals['self']
                        if hasattr(source_obj, '__class__'):
                            source = source_obj.__class__.__name__
                        break
            except Exception:
                pass
            
            # 记录工具调用开始
            tool_name = func.__name__
            args_str = str(args[1:])  # 跳过self参数
            kwargs_str = str(kwargs)
            recursion_logger.log('TOOL_CALL', tool_name, params=f"{args_str}, {kwargs_str}", source=source, tool_name=tool_name)
            
            try:
                # 执行原始函数
                result = func(*args, **kwargs)
                # 记录工具调用结果
                recursion_logger.log('TOOL_RESULT', tool_name, result=str(result), source=source, tool_name=tool_name)
                return result
            except Exception as e:
                # 记录工具调用错误
                recursion_logger.log('TOOL_ERROR', tool_name, result=str(e), source=source, tool_name=tool_name)
                raise
        return wrapper
    
    @staticmethod
    def log_recursion(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取调用来源
            source = "Unknown"
            try:
                if args and hasattr(args[0], '__class__'):
                    source = args[0].__class__.__name__
            except Exception:
                pass
            
            # 记录函数调用开始
            func_name = func.__name__
            recursion_logger.log(f"START: {func_name}()", source=source)
            
            try:
                # 执行原始函数
                result = func(*args, **kwargs)
                # 记录函数调用结束
                recursion_logger.log(f"END: {func_name}()", source=source)
                return result
            except Exception as e:
                # 记录函数调用错误
                recursion_logger.log(f"ERROR: {func_name}() - {str(e)}", source=source)
                raise
        return wrapper
    
    # 递归日志记录功能

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
