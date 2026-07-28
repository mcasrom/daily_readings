import os
import pickle
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer

VECTORIZER_PATH = Path(__file__).parent.parent / "data" / "tfidf_vectorizer.pkl"


class EmbeddingsProvider:
    def __init__(self, mode="test"):
        self.mode = mode
        self._tfidf = None
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._load_vectorizer()

    def _load_vectorizer(self):
        if VECTORIZER_PATH.exists():
            try:
                with open(VECTORIZER_PATH, "rb") as f:
                    self._tfidf = pickle.load(f)
                print(f"  [CACHE] Vectorizer cargado ({self._tfidf.max_features} features)")
            except Exception as e:
                print(f"  [WARN] No se pudo cargar vectorizer: {e}")
                self._tfidf = None

    def _save_vectorizer(self):
        if self._tfidf is not None:
            VECTORIZER_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(VECTORIZER_PATH, "wb") as f:
                pickle.dump(self._tfidf, f)
            print(f"  [OK] Vectorizer guardado ({self._tfidf.max_features} features)")

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
            self._save_vectorizer()
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
