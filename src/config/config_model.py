"""
实体类与配置文件双向映射
"""
from dataclasses import dataclass, field,asdict
from pathlib import Path
from typing import List

import yaml
from cattrs import structure, unstructure

from src.config.config_entity import LLM_Model, MySQL_Config,LangSmith_Config

@dataclass(order=True)
class Project:
    name:str = 'dev'
    max_token_limit: int = 4096 #会话记忆最大长度(超出会自动生成摘要)
    max_steps: int = 10 #迭代次数限制(单次回答)
    llm_model: LLM_Model = field(default_factory=LLM_Model) #语言模型(生产力模型)
    summary_model: LLM_Model = field(default_factory=LLM_Model) #摘要模型(推荐使用本地小模型进行摘要)
    langsmith_config: LangSmith_Config = field(default_factory=LangSmith_Config) #LangSmith配置(监控模型指标)
    mysql: MySQL_Config = field(default_factory=MySQL_Config)

@dataclass
class Config:
    model:str='dev'
    configs:List[Project]=field(default_factory=list)
    
    def get_config(self):
        for _config in self.configs:
            if _config.name == self.model:
                return _config
     
    def load(self, path='config.yaml'):
        if Path(path).exists():
            with open(path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                loaded = structure(data, Config)
                return loaded
        else:
            # 如果文件不存在，才写入默认值
            self.configs.append(Project(name=self.model))
            self.save(path)
            return self

    def save(self, path='config.yaml'):
        data=asdict(self)
        with open(path, 'w') as f:
             yaml.dump(data, f, sort_keys=False, allow_unicode=True)

#配置文件实体类
config_entity =  Config().load()
#获取当前配置(dev、pro...)
config:Project = config_entity.get_config()
config_entity.save() #更新配置文件