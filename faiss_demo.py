import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ==== 1. 文本数据 ====
documents = [
    "成都有很多SLG游戏公司",
    "爱奇艺在成都招聘数据标注实习生",
    "SLG游戏是一种策略类游戏",
    "Python可以用于数据分析和爬虫",
    "Boss直聘是一个招聘网站",
]

# ==== 2. 加载 embedding 模型 ====
print("加载 embedding 模型...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # CPU 模型

# ==== 3. 文本向量化 ====
print("生成向量...")
embeddings = embed_model.encode(documents).astype("float32")

# ==== 4. 创建 FAISS 索引 ====
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
print("向量数量:", index.ntotal)

# ==== 5. 加载 LLM（循环外加载一次） ====
print("加载 LLM 模型...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-0.5B-Instruct")
model_llm = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-0.5B-Instruct",
    torch_dtype="auto",
    device_map="auto"
)

# ==== 6. 查询循环 ====
while True:
    query = input("\n请输入问题(输入exit退出): ")
    if query.lower() == "exit":
        break

    # 6.1 问题向量化
    query_vector = embed_model.encode([query]).astype("float32")

    # 6.2 FAISS 检索最相似文档
    distances, indices = index.search(query_vector, 3)
    context = "\n".join([documents[i] for i in indices[0]])

    # 6.3 拼接 prompt
    prompt = f"""
已知信息：
{context}

请根据以上信息回答问题：
{query}
"""

    # 6.4 LLM 生成回答
    inputs = tokenizer(prompt, return_tensors="pt").to(model_llm.device)
    outputs = model_llm.generate(**inputs, max_new_tokens=200)
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 6.5 输出答案
    print("\n回答：")
    print(answer)
