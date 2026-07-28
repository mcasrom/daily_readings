import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class EmbeddingsProvider:
    def __init__(self, mode="test"):
        self.mode = mode
        self._tfidf = None
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        if self.mode == "production" and self.api_key:
            return self._gemini_embed(texts)
        return self._tfidf_embed(texts)

    def _tfidf_embed(self, texts):
        if self._tfidf is None:
            self._tfidf = TfidfVectorizer(
                max_features=500,
                analyzer="char_wb",
                ngram_range=(2, 4),
                sublinear_tf=True,
                strip_accents="unicode",
            )
            matrix = self._tfidf.fit_transform(texts)
        else:
            matrix = self._tfidf.transform(texts)
        return matrix.toarray().tolist()

    def _gemini_embed(self, texts):
        import google.genai as genai
        client = genai.Client(api_key=self.api_key)
        result = client.models.embed_content(
            model="models/embedding-001",
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def get_tfidf_vectorizer(self):
        return self._tfidf
