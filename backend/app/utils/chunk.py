from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextChunker:
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", " ", ""],
            length_function=len
        )

    def chunk_text(self, text: str, filename: str) -> List[Dict]:
        if not text or not text.strip():
            return []

        chunks = self.splitter.split_text(text)

        chunk_list = []
        for i, chunk in enumerate(chunks):
            chunk_dict = {
                "content": chunk,
                "metadata": {
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
            }
            chunk_list.append(chunk_dict)

        return chunk_list

    def chunk_file(self, file_path: str, text: str) -> List[Dict]:
        import os
        filename = os.path.basename(file_path)
        return self.chunk_text(text, filename)


text_chunker = TextChunker()