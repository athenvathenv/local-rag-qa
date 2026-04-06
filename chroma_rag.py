from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
#用于请求 TronScan API

# ==== 1. 文本数据 ====

original_docs = [
    "成都有很多SLG游戏公司",
    "爱奇艺在成都招聘数据标注实习生",
    "SLG游戏是一种策略类游戏",
    "Python可以用于数据分析和爬虫",
    "Boss直聘是一个招聘网站",
]

import requests
def get_tron_data():
    """从 TronScan 获取最新区块/交易数据"""
    try:
        proxies = {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }
        # TronScan 公开 API（无需密钥）
        url = "https://apilist.tronscanapi.com/api/block"
        params = {
            "limit": 10,  # 拉10条最新区块
            "start": 0
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, headers=headers)
        data = res.json()
        tron_docs = []
        for block in data.get("data", []):
            block_num = block.get("number", 0)
            tx_count = block.get("nrOfTrx", 0)
            timestamp = block.get("timestamp", 0)

            from datetime import datetime
            time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            
            doc = f"Tron区块 {block_num} 包含 {tx_count} 笔交易，生成时间：{time_str}"
            tron_docs.append(doc) 
        return tron_docs
    except Exception as e:
        print("拉取 Tron 数据失败，使用默认数据")
        return ["Tron链是基于DPoS机制的公链", "TRX是波场网络的原生代币"]

# 合并：原有文档 + Tron链上数据
tron_docs = get_tron_data()
documents = original_docs + tron_docs
print("合并后总文档数：", len(documents))
for i, d in enumerate(documents):
    print(f"{i+1}. {d}")


# ==== 2. 加载 embedding 模型 ====
print("加载 embedding 模型...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # CPU 模型

# ==== 3. 文本向量化 ====
print("生成向量...")
embeddings = embed_model.encode(documents).astype("float32")

# ==== 4. 创建 Chroma 向量库====
import chromadb
chroma_client = chromadb.Client()
# 清空旧集合（避免重复）
try:
    chroma_client.delete_collection("tron_rag")
except:
    pass
collection = chroma_client.create_collection(name="tron_rag")

# 添加文档和向量
collection.add(
    embeddings=embeddings.tolist(),
    documents=documents,
    ids=[str(i) for i in range(len(documents))]
)
print("向量数量:", collection.count())

# ==== 5. 加载 LLM（循环外加载一次） ====
print("加载 LLM 模型...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-0.5B-Instruct", trust_remote_code=True)
model_llm = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-0.5B-Instruct",
    torch_dtype="auto",
    device_map="auto",
    trust_remote_code=True
)

# ==== 6. 查询循环 ====
while True:
    query = input("\n请输入问题(输入exit退出): ")
    if query.lower() == "exit":
        break

    # 6.1 问题向量化
    query_vector = embed_model.encode([query]).astype("float32")

    # 6.2 Chroma 检索（修复缩进：放在循环里面！）
    query_embedding = embed_model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=5
    )
    candidates = results['documents'][0]

    # 智能逻辑：问 Tron 最新区块 → 自动取区块号最大
    if "Tron区块" in query or "最新" in query:
        tron_list = []
        for doc in candidates:
            if "Tron区块" in doc:
                try:
                    block_num = int(doc.split("Tron区块 ")[1].split(" ")[0])
                    tron_list.append((block_num, doc))
                except:
                    pass
        if tron_list:
            tron_list.sort(reverse=True)
            context = tron_list[0][1]
        else:
            context = "\n".join(candidates)
    else:
        context = "\n".join(candidates)

    # 6.3 拼接 prompt
    prompt = f"""
已知信息：
{context}

请根据以上信息回答问题：
{query}
"""

    # 6.4 LLM 生成回答
    inputs = tokenizer(prompt, return_tensors="pt").to(model_llm.device)
    outputs = model_llm.generate(
        **inputs,
        max_new_tokens=64,
        temperature=0.1,
        top_p=0.95,
        pad_token_id=tokenizer.eos_token_id
    )
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 6.5 输出答案
    print("\n回答：")
    print(answer)
