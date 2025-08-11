import os
import ssl
import logging
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.prebuilt import create_react_agent

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 读取敏感信息
api_url = os.getenv("OPENAI_API_BASE", "https://gateway.ai-uat.mcdchina.net/one-api/v1")
api_key = os.getenv(
    "OPENAI_API_KEY", "sk-yeZQx7cBgPRvN5Sj558fE306CfC440A990C358133017E04f"
)


# 创建SSL上下文，禁用证书验证
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 初始化LLM
llm = ChatOpenAI(
    model="gpt-4.1",
    base_url=api_url,
    temperature=0,
    default_headers={"User-Agent": "langchain-openai/1.0.0"},
    http_client=None,  # 直接用默认即可，httpx.Client(verify=False) 仅在特殊场景下需要
)

# 数据库连接配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.198.174")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "Fin_Chatbi")

mysql_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"


def get_database():
    try:
        db = SQLDatabase.from_uri(mysql_uri)
        logging.info("成功连接到MySQL数据库")
        return db
    except Exception as e:
        logging.error(f"连接MySQL数据库失败: {e}")
        raise RuntimeError("数据库连接失败，请检查配置。")


def main():
    db = get_database()
    logging.info(f"Dialect: {db.dialect}")
    logging.info(f"Available tables: {db.get_usable_table_names()}")
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    for tool in tools:
        logging.info(f"{tool.name}: {tool.description}\n")
    system_prompt = f"""
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {db.dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most 10 results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
"""
    agent = create_react_agent(
        llm,
        tools,
        state_modifier=system_prompt,
    )
    question = "请列出 RunNO=1、RunNO=2 和 RunNO=3 的 ANP 摘要"
    for step in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        # 直接打印最后一条消息内容
        print(
            step["messages"][-1].content
            if hasattr(step["messages"][-1], "content")
            else step["messages"][-1]
        )


if __name__ == "__main__":
    main()
