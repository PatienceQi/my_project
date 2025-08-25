import os
from neo4j import GraphDatabase
import dotenv

dotenv.load_dotenv()

# 获取Neo4j连接信息
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

# 创建Neo4j驱动程序
def create_driver():
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        print("Connection to Neo4j successful!")
        return driver
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return None

# 测试连接
driver = create_driver()
if driver:
    driver.close()