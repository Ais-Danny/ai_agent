from langchain.chat_models import init_chat_model
from dataclasses import dataclass
import pymysql,os

@dataclass(order=True)
class LLM_Model:
    model_name:str = ""
    model_provider: str = "openai" # 格式
    base_url: str = None
    key: str = None
    temperature: float = 0

    def init_model(self):
        _model=init_chat_model(
            model= self.model_name,
            model_provider= self.model_provider,
            base_url= self.base_url, 
            api_key=self.key,
            temperature=self.temperature
            )
        return _model

@dataclass
class MySQL_Config:
    host: str = "192.168.3.26"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    database: str = "agent_db"

    def get_conn(self):
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
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_PROJECT: str = "agent_project"
    LANGCHAIN_API_KEY: str = "" #你在 LangSmith  Key
    def init_env(self):
        os.environ["LANGCHAIN_TRACING_V2"] = self.LANGCHAIN_TRACING_V2
        os.environ["LANGCHAIN_PROJECT"] = self.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_API_KEY"] = self.LANGCHAIN_API_KEY