import os
import pickle
import tempfile
import shutil
import faiss
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime
from ..models.knowledge_base import KnowledgeDocument
from ..core.config import settings, UPLOAD_PATH, INDEX_PATH
from ..utils.ocr_parse import ocr_parser
from ..utils.chunk import text_chunker
from ..utils.embedding import get_text_embedder


class KnowledgeBaseService:
    def __init__(self):
        self.index_cache = {}
        self.next_id_cache = {}

    def _get_index_path(self, user_id: int) -> str:
        user_index_path = INDEX_PATH / str(user_id)
        user_index_path.mkdir(parents=True, exist_ok=True)
        return str(user_index_path)

    def _load_index(self, user_id: int):
        index_path = self._get_index_path(user_id)
        index_file = os.path.join(index_path, "index.faiss")
        metadata_file = os.path.join(index_path, "index.pkl")
        vocab_file = os.path.join(index_path, "vocab.pkl")

        if user_id in self.index_cache:
            return self.index_cache[user_id]

        if os.path.exists(index_file) and os.path.exists(metadata_file):
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_index_file = os.path.join(tmp_dir, "index.faiss")
                    tmp_metadata_file = os.path.join(tmp_dir, "index.pkl")
                    tmp_vocab_file = os.path.join(tmp_dir, "vocab.pkl")
                    shutil.copy(index_file, tmp_index_file)
                    shutil.copy(metadata_file, tmp_metadata_file)

                    index = faiss.read_index(tmp_index_file)
                    with open(tmp_metadata_file, 'rb') as f:
                        metadata = pickle.load(f)

                    if os.path.exists(vocab_file):
                        shutil.copy(vocab_file, tmp_vocab_file)
                        with open(tmp_vocab_file, 'rb') as f:
                            vocab_data = pickle.load(f)
                        embedder = get_text_embedder()
                        embedder.simple_embedder.vocab = vocab_data.get("vocab", {})
                        embedder.simple_embedder.idf = vocab_data.get("idf", {})
                        embedder.simple_embedder.dim = vocab_data.get("dim", 384)
                        embedder.simple_embedder.fixed_vocab = True

                if hasattr(index, 'ntotal') and index.ntotal > 0:
                    if isinstance(index, faiss.IndexIDMap2):
                        self.index_cache[user_id] = {"index": index, "metadata": metadata}
                        max_id = 0
                        for meta in metadata:
                            if meta.get("faiss_id", 0) > max_id:
                                max_id = meta["faiss_id"]
                        self.next_id_cache[user_id] = max_id + 1
                        return self.index_cache[user_id]
                    elif isinstance(index, faiss.IndexFlat):
                        self.index_cache[user_id] = {"index": index, "metadata": metadata}
                        self.next_id_cache[user_id] = index.ntotal
                        return self.index_cache[user_id]
                    else:
                        print(f"Unknown index type for user {user_id}: {type(index)}")
            except Exception as e:
                print(f"Failed to load index for user {user_id}: {e}")

        return {"index": None, "metadata": []}

    def _save_index(self, user_id: int, index: faiss.Index, metadata: list):
        index_path = self._get_index_path(user_id)
        os.makedirs(index_path, exist_ok=True)
        index_file = os.path.join(index_path, "index.faiss")
        metadata_file = os.path.join(index_path, "index.pkl")
        vocab_file = os.path.join(index_path, "vocab.pkl")

        embedder = get_text_embedder()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_index_file = os.path.join(tmp_dir, "index.faiss")
            tmp_metadata_file = os.path.join(tmp_dir, "index.pkl")
            tmp_vocab_file = os.path.join(tmp_dir, "vocab.pkl")

            faiss.write_index(index, tmp_index_file)
            with open(tmp_metadata_file, 'wb') as f:
                pickle.dump(metadata, f)

            vocab_data = {
                "vocab": embedder.simple_embedder.vocab,
                "idf": embedder.simple_embedder.idf,
                "dim": embedder.simple_embedder.dim
            }
            with open(tmp_vocab_file, 'wb') as f:
                pickle.dump(vocab_data, f)

            shutil.copy(tmp_index_file, index_file)
            shutil.copy(tmp_metadata_file, metadata_file)
            shutil.copy(tmp_vocab_file, vocab_file)

        self.index_cache[user_id] = {"index": index, "metadata": metadata}

    def add_document(self, db: Session, user_id: int, file_content: bytes, filename: str, subject: str = "未分类", index_now: bool = False) -> dict:
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        file_size = len(file_content)

        UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

        storage_path = UPLOAD_PATH / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        with open(storage_path, 'wb') as f:
            f.write(file_content)

        resource = KnowledgeDocument(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=str(storage_path),
            subject=subject
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)

        if index_now:
            self._index_document(db, user_id, resource)

        return self._to_dict(resource)

    def _index_document(self, db: Session, user_id: int, resource: KnowledgeDocument, progress_callback=None):
        try:
            index_rebuilt = False

            def check_cancel():
                if progress_callback:
                    progress_callback(0, "检查取消状态")

            if resource.indexed_at:
                check_cancel()
                if progress_callback:
                    progress_callback(5, "检测到已有索引，正在清理...")

                index_data = self._load_index(user_id)
                if index_data["index"] is not None and index_data["metadata"]:
                    index = index_data["index"]

                    if isinstance(index, faiss.IndexIDMap2):
                        ids_to_remove = []
                        indices_to_remove = []
                        for idx, meta in enumerate(index_data["metadata"]):
                            if meta.get("document_id") == resource.id:
                                faiss_id = meta.get("faiss_id")
                                if faiss_id:
                                    ids_to_remove.append(faiss_id)
                                indices_to_remove.append(idx)

                        if ids_to_remove:
                            index.remove_ids(np.array(ids_to_remove, dtype=np.int64))

                        if indices_to_remove:
                            indices_to_remove.sort(reverse=True)
                            for idx in indices_to_remove:
                                index_data["metadata"].pop(idx)

                            self._save_index(user_id, index, index_data["metadata"])
                    elif isinstance(index, faiss.IndexFlat):
                        if progress_callback:
                            progress_callback(5, "检测到旧格式索引，正在全量重建...")
                        self._rebuild_index(db, user_id)
                        index_rebuilt = True
                        if progress_callback:
                            progress_callback(15, "索引格式已转换，文档已重新索引")
                    else:
                        if progress_callback:
                            progress_callback(5, "正在全量重建索引...")
                        self._rebuild_index(db, user_id)
                        index_rebuilt = True
                        if progress_callback:
                            progress_callback(15, "索引已重建")

            if index_rebuilt:
                resource.chunk_count = self._get_document_chunk_count(db, resource.id)
                resource.indexed_at = datetime.utcnow()
                db.commit()
                if progress_callback:
                    progress_callback(100, "索引完成")
                return

            check_cancel()
            if progress_callback:
                progress_callback(5, "开始解析文档...")

            text = ocr_parser.parse_file(resource.storage_path, progress_callback)

            check_cancel()
            if progress_callback:
                progress_callback(20, "文档解析完成")

            if text:
                chunks = text_chunker.chunk_file(resource.storage_path, text)

                check_cancel()
                if progress_callback:
                    progress_callback(30, f"文档分块完成，共 {len(chunks)} 个分块")

                if chunks:
                    for chunk in chunks:
                        chunk["metadata"]["subject"] = resource.subject or "未分类"
                        chunk["metadata"]["document_id"] = resource.id

                    contents = [chunk["content"] for chunk in chunks]

                    try:
                        check_cancel()
                        if progress_callback:
                            progress_callback(40, "开始生成向量嵌入...")

                        embeddings = get_text_embedder().embed_texts(contents)

                        check_cancel()
                        if progress_callback:
                            progress_callback(80, "向量生成完成")

                        if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 1:
                            check_cancel()
                            if progress_callback:
                                progress_callback(85, "正在保存索引...")

                            embeddings_np = np.array(embeddings)
                            self._add_to_index(user_id, embeddings_np, chunks)

                            if progress_callback:
                                progress_callback(90, "索引保存完成")

                            resource.chunk_count = len(chunks)
                            resource.indexed_at = datetime.utcnow()
                            db.commit()

                            if progress_callback:
                                progress_callback(95, "数据库更新完成")
                        else:
                            print(f"Embedding returned zeros, skipping index for document {resource.id}")
                            if progress_callback:
                                progress_callback(0, "向量生成失败，跳过索引")
                    except Exception as embed_e:
                        if "取消" in str(embed_e) or "cancelled" in str(embed_e).lower():
                            raise
                        print(f"Embedding failed for document {resource.id}: {embed_e}")
                        if progress_callback:
                            progress_callback(0, f"向量生成失败: {str(embed_e)}")
            else:
                if progress_callback:
                    progress_callback(0, "文档解析失败，未提取到文本")
        except Exception as e:
            if "取消" in str(e) or "cancelled" in str(e).lower():
                print(f"Index cancelled for document {resource.id}")
                raise Exception("用户已取消索引")
            print(f"Indexing failed for document {resource.id}: {e}")
            if progress_callback:
                progress_callback(0, f"索引失败: {str(e)}")

    def index_document(self, db: Session, user_id: int, document_id: int, progress_callback=None) -> bool:
        document = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.user_id == user_id
        ).first()

        if not document:
            return False

        self._index_document(db, user_id, document, progress_callback)
        return True

    def _get_document_chunk_count(self, db: Session, document_id: int) -> int:
        document = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id
        ).first()

        if not document or not document.storage_path:
            return 0

        try:
            text = ocr_parser.parse_file(document.storage_path)
            if text:
                chunks = text_chunker.chunk_file(document.storage_path, text)
                return len(chunks) if chunks else 0
        except Exception as e:
            print(f"Failed to get chunk count for document {document_id}: {e}")

        return document.chunk_count or 0

    def _add_to_index(self, user_id: int, embeddings: np.ndarray, chunks: list):
        index_data = self._load_index(user_id)
        index = index_data["index"]
        metadata = index_data["metadata"]

        if user_id not in self.next_id_cache:
            self.next_id_cache[user_id] = 1

        if index is None:
            dimension = embeddings.shape[1]
            flat_index = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIDMap2(flat_index)

        ids = np.arange(self.next_id_cache[user_id], self.next_id_cache[user_id] + len(embeddings))
        index.add_with_ids(embeddings, ids)

        for i, chunk in enumerate(chunks):
            chunk["metadata"]["faiss_id"] = int(ids[i])
            metadata.append(chunk["metadata"])

        self.next_id_cache[user_id] += len(embeddings)
        self._save_index(user_id, index, metadata)

    def remove_document(self, db: Session, user_id: int, document_id: int) -> bool:
        document = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.user_id == user_id
        ).first()

        if not document:
            return False

        # 1. 删除索引中的向量
        index_data = self._load_index(user_id)
        if index_data["index"] is not None and index_data["metadata"]:
            ids_to_remove = []
            indices_to_remove = []
            for idx, meta in enumerate(index_data["metadata"]):
                if meta.get("document_id") == document.id:
                    faiss_id = meta.get("faiss_id")
                    if faiss_id:
                        ids_to_remove.append(faiss_id)
                    indices_to_remove.append(idx)

            if ids_to_remove:
                index_data["index"].remove_ids(np.array(ids_to_remove, dtype=np.int64))

            if indices_to_remove:
                indices_to_remove.sort(reverse=True)
                for idx in indices_to_remove:
                    index_data["metadata"].pop(idx)

                self._save_index(user_id, index_data["index"], index_data["metadata"])

        # 2. 先从数据库删除，确保重建索引时不会包含该文档
        db.delete(document)
        db.commit()

        # 3. 删除物理文件
        if os.path.exists(document.storage_path):
            try:
                os.remove(document.storage_path)
            except Exception as e:
                print(f"Failed to remove file {document.storage_path}: {e}")

        # 4. 清除索引缓存，确保下次搜索加载最新索引
        if user_id in self.index_cache:
            del self.index_cache[user_id]

        return True

    def rebuild_index_async(self, user_id: int):
        """在后台重建索引，不阻塞主线程"""
        try:
            from ..core.database import SessionLocal
            db = SessionLocal()
            try:
                self._rebuild_index(db, user_id)
            finally:
                db.close()
        except Exception as e:
            print(f"Async index rebuild failed for user {user_id}: {e}")

    def _rebuild_index(self, db: Session, user_id: int):
        documents = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.user_id == user_id
        ).all()

        all_embeddings = []
        all_metadata = []

        for doc in documents:
            # 跳过物理文件已不存在的文档
            if not os.path.exists(doc.storage_path):
                print(f"Skipping missing file: {doc.storage_path}")
                continue

            try:
                text = ocr_parser.parse_file(doc.storage_path)
                if text:
                    chunks = text_chunker.chunk_file(doc.storage_path, text)
                    if chunks:
                        contents = [chunk["content"] for chunk in chunks]
                        embeddings = get_text_embedder().embed_texts(contents)
                        if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 1:
                            all_embeddings.append(embeddings)
                            for chunk in chunks:
                                chunk["metadata"]["subject"] = doc.subject or "未分类"
                                chunk["metadata"]["document_id"] = doc.id
                                all_metadata.append(chunk["metadata"])
            except Exception as e:
                print(f"Failed to rebuild index for document {doc.id} ({doc.filename}): {e}")
                continue

        if all_embeddings:
            combined_embeddings = np.vstack(all_embeddings)
            dimension = combined_embeddings.shape[1]
            flat_index = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIDMap2(flat_index)

            ids = np.arange(1, len(combined_embeddings) + 1)
            index.add_with_ids(combined_embeddings, ids)

            for i, meta in enumerate(all_metadata):
                meta["faiss_id"] = int(ids[i])

            self.next_id_cache[user_id] = len(combined_embeddings) + 1
            self._save_index(user_id, index, all_metadata)
        else:
            if user_id in self.index_cache:
                del self.index_cache[user_id]
            index_path = self._get_index_path(user_id)
            for f in ["index.faiss", "index.pkl", "vocab.pkl"]:
                fp = os.path.join(index_path, f)
                if os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass

    def get_documents(self, db: Session, user_id: int, subject: str = None) -> list:
        query = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.user_id == user_id
        )
        if subject and subject != "全部":
            query = query.filter(KnowledgeDocument.subject == subject)
        documents = query.order_by(KnowledgeDocument.created_at.desc()).all()
        return [self._to_dict(doc) for doc in documents]

    def get_document(self, db: Session, user_id: int, document_id: int) -> dict:
        document = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.user_id == user_id
        ).first()
        return self._to_dict(document) if document else None

    def search(self, user_id: int, query: str, top_k: int = 3, threshold: float = 0.1, subject: str = None, enable_keyword_fallback: bool = True) -> list:
        index_data = self._load_index(user_id)
        index = index_data["index"]
        metadata = index_data["metadata"]

        if index is None or index.ntotal == 0:
            return []

        simplified_query = self._simplify_query(query)

        keyword_results = self._keyword_search(simplified_query, metadata, top_k * 3, subject)

        if not keyword_results:
            search_top_k = top_k * 5
            query_vector = get_text_embedder().embed_text(simplified_query)
            query_vector = np.array([query_vector])
            distances, indices = index.search(query_vector, search_top_k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx < 0 or idx >= len(metadata):
                    continue
                distance = distances[0][i]
                similarity = 1 / (1 + distance)
                if similarity >= threshold:
                    if subject and subject != "全部":
                        meta = metadata[idx]
                        if meta.get("subject", "未分类") != subject:
                            continue
                    meta = metadata[idx]
                    results.append({
                        "content": meta.get("content", ""),
                        "metadata": meta,
                        "similarity": float(similarity)
                    })
            return results[:top_k]

        keyword_results.sort(key=lambda x: x["similarity"], reverse=True)
        return keyword_results[:top_k]

    def _simplify_query(self, query: str) -> str:
        import re
        q = query.strip()
        suffixes_to_remove = [
            '的题目', '的题', '的问题', '的内容', '的知识点', '的相关内容',
            '是什么', '有哪些', '请列出', '请介绍', '请说明', '求', '计算',
        ]
        for suffix in suffixes_to_remove:
            if q.endswith(suffix) and len(q) > len(suffix) + 1:
                q = q[:-len(suffix)]
                break

        q = re.sub(r'[的了呢吗啊吧呀哦]+$', '', q)
        q = re.sub(r'[，,。.！!？?、：:；;]+$', '', q)

        return q.strip()

    def _extract_chinese_phrases(self, text: str) -> list:
        import re
        phrases = []
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        for chunk in chinese:
            n = len(chunk)
            for length in range(min(n, 4), 1, -1):
                for i in range(n - length + 1):
                    phrases.append(chunk[i:i+length])
        return phrases

    def _keyword_search(self, query: str, metadata: list, top_k: int, subject: str = None) -> list:
        import re

        query_lower = query.lower()

        phrases = self._extract_chinese_phrases(query_lower)
        english_words = re.findall(r'[a-zA-Z]+', query_lower)

        core_terms = []
        seen = set()
        for p in sorted(phrases, key=len, reverse=True):
            if p not in seen:
                core_terms.append(p)
                seen.add(p)
        for w in english_words:
            if w not in seen:
                core_terms.append(w)
                seen.add(w)

        if not core_terms:
            return []

        query_len = len(query_lower)

        three_char_phrases = [p for p in phrases if len(p) == 3]
        two_char_phrases = [p for p in phrases if len(p) == 2]

        if query_len >= 4:
            max_base = 20.0
        elif query_len == 3:
            max_base = 12.0
        else:
            max_base = 6.0

        max_possible = max_base + len(three_char_phrases) * 2.5 + len(two_char_phrases) * 1.5 + 15.0 + 8.0

        scored_chunks = []

        for meta in metadata:
            content = meta.get("content", "").lower()
            if not content:
                continue

            if subject and subject != "全部":
                doc_subject = meta.get("subject", "未分类")
                if doc_subject != subject:
                    continue

            has_exact = query_lower in content

            matched_phrases = []
            phrase_positions = {}

            for term in core_terms:
                if len(term) >= 2:
                    pos = content.find(term)
                    if pos >= 0:
                        matched_phrases.append(term)
                        phrase_positions[term] = pos

            if not matched_phrases:
                continue

            best_match_len = max(len(p) for p in matched_phrases)

            if not has_exact and best_match_len < 2:
                continue

            score = 0.0

            if best_match_len >= 4:
                score += 20.0
            elif best_match_len == 3:
                score += 12.0
            elif best_match_len == 2:
                score += 6.0

            three_char_matches = sum(1 for p in matched_phrases if len(p) == 3)
            two_char_matches = sum(1 for p in matched_phrases if len(p) == 2)
            score += three_char_matches * 2.5
            score += two_char_matches * 1.5

            if has_exact:
                score += 15.0

            if len(matched_phrases) >= 2:
                positions = [phrase_positions[p] for p in matched_phrases]
                min_pos = min(positions)
                max_pos = max(positions)
                spread = max_pos - min_pos
                if len(content) > 0:
                    proximity = max(0, 1.0 - spread / (len(content) * 0.3))
                    score += proximity * 8.0

            effective_max = max_possible
            similarity = min(score / max(effective_max, 1.0), 1.0)

            scored_chunks.append({
                "content": meta.get("content", ""),
                "metadata": meta,
                "similarity": similarity,
                "keyword_score": score,
                "matched_phrases": matched_phrases
            })

        scored_chunks.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
        return scored_chunks[:top_k]

    def get_status(self, db: Session, user_id: int) -> dict:
        documents = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.user_id == user_id
        ).all()

        total_chunks = sum(doc.chunk_count or 0 for doc in documents)

        index_data = self._load_index(user_id)
        index_size = index_data["index"].ntotal if index_data["index"] else 0

        return {
            "document_count": len(documents),
            "total_chunks": total_chunks,
            "index_size": index_size,
            "documents": [self._to_dict(doc) for doc in documents]
        }

    def _to_dict(self, document: KnowledgeDocument) -> dict:
        return {
            "id": document.id,
            "user_id": document.user_id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "storage_path": document.storage_path,
            "subject": document.subject or "未分类",
            "chunk_count": document.chunk_count,
            "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
            "created_at": document.created_at.isoformat() if document.created_at else None
        }


knowledge_base_service = KnowledgeBaseService()