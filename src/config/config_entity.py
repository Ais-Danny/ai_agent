from typing import Optional
from langchain.chat_models import init_chat_model
from dataclasses import dataclass
import pymysql
import os


@dataclass(order=True)
class LLM_Model:
    """语言模型配置"""
    model_name: str = ""
    model_provider: str = "openai"  # 模型提供商
    base_url: Optional[str] = None  # API基础URL
    key: Optional[str] = None  # API密钥
    temperature: float = 0.0  # 生成温度

    def init_model(self):
        """初始化语言模型"""
        return init_chat_model(
            model=self.model_name,
            model_provider=self.model_provider,
            base_url=self.base_url, 
            api_key=self.key,
            temperature=self.temperature
        )


@dataclass
class MySQL_Config:
    """MySQL数据库配置"""
    host: str = "192.168.3.26"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    database: str = "agent_db"

    def get_conn(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            autocommit=True
        )
    

@dataclass
class LangSmith_Config:
    """LangSmith监控配置"""
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_PROJECT: str = "agent_project"
    LANGCHAIN_API_KEY: str = ""  # LangSmith API Key
    
    def init_env(self):
        """初始化LangSmith环境变量"""
        os.environ["LANGCHAIN_TRACING_V2"] = self.LANGCHAIN_TRACING_V2.lower()
        os.environ["LANGCHAIN_PROJECT"] = self.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_API_KEY"] = self.LANGCHAIN_API_KEY