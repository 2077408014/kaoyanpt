import os
import math
import re
from typing import List


class SimpleEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vocab = {}
        self.idf = {}
        self.fixed_vocab = False

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r'[a-zA-Z]+[\w]*|[\u4e00-\u9fff]+', text)
        result = []
        for t in tokens:
            if len(t) >= 2:
                result.append(t)
            if re.match(r'[\u4e00-\u9fff]+', t):
                for n in range(1, min(len(t) + 1, 5)):
                    for i in range(len(t) - n + 1):
                        result.append(t[i:i+n])
        return result

    def _build_vocab(self, texts: List[str], update_only: bool = False):
        if self.fixed_vocab and not update_only:
            return

        doc_count = len(texts) + len(self.vocab)

        for text in texts:
            tokens = set(self._tokenize(text))
            for token in tokens:
                self.vocab[token] = self.vocab.get(token, 0) + 1

        for token in self.vocab:
            self.idf[token] = math.log(doc_count / (self.vocab[token] + 1))

    def _text_to_vec(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = self._tokenize(text)
        if not tokens:
            return vec

        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        avg_idf = sum(self.idf.values()) / len(self.idf) if self.idf else 1.0

        for token in tokens:
            idx = hash(token) % self.dim
            idf_val = self.idf.get(token, avg_idf)
            tfidf = tf[token] * idf_val

            token_len = len(token)
            if re.match(r'[\u4e00-\u9fff]+', token):
                if token_len == 1:
                    weight = 0.3
                elif token_len == 2:
                    weight = 0.8
                elif token_len == 3:
                    weight = 1.2
                else:
                    weight = 1.5
            else:
                weight = 1.0

            vec[idx] += tfidf * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def embed_text(self, text: str) -> List[float]:
        return self._text_to_vec(text)

    def embed_texts(self, texts: List[str], build_vocab: bool = True) -> List[List[float]]:
        if build_vocab:
            self._build_vocab(texts)
        return [self._text_to_vec(text) for text in texts]

    def fix_vocab(self):
        self.fixed_vocab = True


class TextEmbedder:
    def __init__(self, model_name: str = "simple-tfidf"):
        self.model_name = model_name
        self.simple_embedder = SimpleEmbedder()

    def embed_text(self, text: str):
        return self.simple_embedder.embed_text(text)

    def embed_texts(self, texts: List[str]):
        return self.simple_embedder.embed_texts(texts)

    def fix_vocab(self):
        self.simple_embedder.fix_vocab()


text_embedder = None


def get_text_embedder() -> TextEmbedder:
    global text_embedder
    if text_embedder is None:
        text_embedder = TextEmbedder()
    return text_embedder