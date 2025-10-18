# Agent 智能体


### 1.依赖下载
- python 环境 3.13.1

``` shell
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```


### 2.配置文件
- 配置文件路径：config.yaml
- langsmith 在https://smith.langchain.com/申请key 进行查询模型指标
- 配置文件内容：
```yaml
model: dev # 启用的环境
configs:
- name: dev  # 环境名称
  max_token_limit: 2048 # 历史会话大小达到该值时进行摘要处理以节省token消耗
  llm_model: # 语言模型配置
    model_name: deepseek-v3.1:671b-cloud # 模型名称
    model_provider: ollama # api 格式(ollama/openai)
    base_url: http://127.0.0.1:11434 # 模型服务地址(ollama直接填写地址端口 openai需要详细到具体路由/v1)
    key: '' # 模型服务key
    temperature: 0.0 # 模型生成的随机性(越大具有创造性,回答想象力越丰富)
  summary_model: # 摘要模型配置(建议使用本地小型模型进行摘要,以节省token消耗)
    model_name: deepseek-v3.1:671b-cloud
    model_provider: ollama
    base_url: http://127.0.0.1:11434
    key: ''
    temperature: 0.0
  langsmith_config: # 模型监控指标
    LANGCHAIN_TRACING_V2: 'ture' # 是否开启模型监控(生产环境可关闭)
    LANGCHAIN_PROJECT: agent_project # 项目名称
    LANGCHAIN_API_KEY: '' # LangSmith api_key
  mysql: # mysql配置(预留暂未启用)
    host: git.aisdanny.top
    port: 3306
    user: root
    password: root
    database: agent_db
```