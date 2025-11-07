import os
import subprocess
from langchain_core.tools import tool


@tool
def list_files(directory: str) -> str:
    """列出指定目录下的所有文件和子目录"""
    try:
        return "\n".join(os.listdir(directory))
    except Exception as e:
        return f"错误: {str(e)}"


@tool
def read_file(file_path: str) -> str:
    """读取指定文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"错误: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """将指定内容写入文件，如果文件已存在则覆盖"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件已写入成功: {file_path}"
    except Exception as e:
        return f"错误: {str(e)}"
    

@tool
def run_cmd(command: str) -> str:
    """
    执行 Windows cmd 命令，并返回输出。
    """
    try:
        # 执行命令
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True
        )

        # 拼接 stdout 和 stderr
        output_parts = []
        if result.stdout.strip():
            output_parts.append(result.stdout.strip())
        if result.stderr.strip():
            output_parts.append(result.stderr.strip())
            
        output = "\n".join(output_parts)

        # 如果内容为空，返回提示
        if not output:
            return f"命令已执行成功，但没有输出: {command}"
        
        return output
    except Exception as e:
        return f"命令执行异常: {str(e)}"