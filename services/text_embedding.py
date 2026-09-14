# utils/embedding_matcher.py

import numpy as np
import faiss
import os
import pickle
from config.model_provider import create_embedding_model


def find_best_match_indices(text: str, candidates: list) -> list:
    """
    输入一个text和一个候选列表，通过embedding和index技术返回所有候选项的索引，按相似度从高到低排序
    :param text: 待匹配文本
    :param candidates: 候选文本列表
    :param embed_fn: 一个将文本转为embedding的函数
    :return: 所有候选项的索引列表，按相似度从高到低排序
    """
    if not candidates: # 如果候选列表为空 返回空列表
        return []
    candidate_embs = [embed_input(c) for c in candidates]  # 遍历候选文本，使用embed_input转向量
    candidate_embs = np.array(candidate_embs).astype("float32")  # 再转为numpy数组
    dimension = candidate_embs.shape[1]  # 获取向量维度
    index = faiss.IndexFlatL2(dimension)  # 创建Faiss索引
    index.add(candidate_embs)   # 把所有候选向量加入索引库，建立快速检索结构
    text_emb = np.array([embed_input(text)]).astype("float32")  # 将输入文本也转为向量 包裹成二维数组
    k = len(candidates)
    _, indices = index.search(text_emb, k)  # 在索引中找与输入向量最相似的 k 个候选
    return indices[0][:k].tolist()

# 将文本转向量
def embed_input(input_text: str, model: str = "text-embedding-ada-002",
                encoding_format: str = "float", dimensions: int = None,
                timeout: int = 600) -> list:
    embeddings = create_embedding_model()
    return embeddings.embed_query(input_text)


def save_technician_embeddings(embeddings, indices, path="data/technician_embeddings.pkl"):
    """
    保存技师嵌入向量和索引到本地
    """
    with open(path, "wb") as f:
        pickle.dump({"embeddings": embeddings, "indices": indices}, f)


def load_technician_embeddings(path="data/technician_embeddings.pkl"):
    """
    加载本地保存的技师嵌入向量和索引
    """
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = pickle.load(f)
        return data.get("embeddings"), data.get("indices")
