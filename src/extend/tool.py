import os,subprocess
from langchain_core.tools import tool

from langchain_experimental.tools import PythonREPLTool
from langchain_community.tools import ShellTool


# ----------------- 工具 -----------------
@tool
def list_files(directory: str) -> str:
    """列出指定目录下的所有文件和子目录"""
    try:
        return "\n".join(os.listdir(directory))
    except Exception as e:
        return f"错误: {e}"

@tool
def read_file(file_path: str) -> str:
    """读取指定文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"错误: {e}"
@tool
def write_file(file_path: str, content: str) -> str:
    """将指定内容写入文件，如果文件已存在则覆盖"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件已写入成功: {file_path}"
    except Exception as e:
        return f"错误: {e}"
    
@tool
def run_cmd(command: str) -> str:
    """
    执行 Windows cmd 命令，并返回输出
    """
    try:
        # 执行命令
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        # 返回标准输出和错误输出
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)