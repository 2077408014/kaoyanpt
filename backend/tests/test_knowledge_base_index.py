"""回归测试：资料管理索引必须持久化分块正文。

背景：索引元数据此前只保存 filename/chunk_index 等字段，未保存分块正文
（content），导致 FAISS 能召回分块但检索结果 content 恒为空，
RAG 上下文为空、"好多东西检索不到"。

运行方式（无需 pytest）：
    python3 backend/tests/test_knowledge_base_index.py
"""

import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from app.utils.chunk import text_chunker
from app.utils.embedding import get_text_embedder
from app.services.knowledge_base_service import KnowledgeBaseService


def test_chunk_metadata_contains_content():
    """分块元数据必须携带正文内容，供索引持久化。"""
    text = "极限是数学分析的灵魂，贯穿整个理论体系。" * 50
    chunks = text_chunker.chunk_text(text, "test.txt")
    assert chunks, "应产生分块"
    for chunk in chunks:
        assert chunk["metadata"].get("content"), "分块元数据必须包含正文内容"
        assert chunk["metadata"]["content"] == chunk["content"]


def test_index_search_returns_non_empty_content():
    """建立索引后，检索结果必须返回非空正文。"""
    service = KnowledgeBaseService()
    tmp_dir = tempfile.mkdtemp()
    try:
        service._get_index_path = lambda user_id: tmp_dir

        text = "极限思想贯穿整个数学分析体系，是微分学与积分学的理论基石。" * 40
        chunks = text_chunker.chunk_text(text, "极限.txt")
        for chunk in chunks:
            chunk["metadata"]["subject"] = "数学"
            chunk["metadata"]["document_id"] = 1

        contents = [chunk["content"] for chunk in chunks]
        embeddings = get_text_embedder().embed_texts(contents)
        service._add_to_index(999, np.array(embeddings), chunks)

        results = service.search(999, "极限思想", top_k=3)
        assert results, "应检索到结果"
        assert all(r["content"] for r in results), "检索结果必须包含正文"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    test_chunk_metadata_contains_content()
    test_index_search_returns_non_empty_content()
    print("PASS: test_knowledge_base_index")


if __name__ == "__main__":
    main()
