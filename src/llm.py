import os
import json
import hashlib
import requests


class LLMProvider:
    def __init__(self, mode='test', groq_model='llama3-70b-8192'):
        self.mode = mode
        self.groq_model = groq_model
        self._cache_enabled = True
        if mode == 'production':
            self.groq_key = os.environ.get('GROQ_API_KEY')
            if not self.groq_key:
                raise ValueError('GROQ_API_KEY no configurada')
        else:
            self.ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
            self.ollama_model = os.environ.get('OLLAMA_LLM_MODEL', 'tinyllama')

    def _cache_key(self, prompt):
        return hashlib.md5(prompt.encode()).hexdigest()

    def _check_cache(self, prompt):
        if not self._cache_enabled:
            return None
        try:
            from src.db import get_llm_cache
            return get_llm_cache(self._cache_key(prompt))
        except Exception:
            return None

    def _save_cache(self, prompt, result):
        if not self._cache_enabled:
            return
        try:
            from src.db import set_llm_cache
            set_llm_cache(self._cache_key(prompt), result)
        except Exception:
            pass

    def _truncate_titles(self, titles, max_chars=2000):
        result = []
        total = 0
        for t in titles:
            t = t.strip()
            if total + len(t) > max_chars:
                break
            result.append(t)
            total += len(t)
        return result

    def label_cluster(self, titles, lang='es'):
        titles = self._truncate_titles(titles, 1500)
        prompt = f'Resume en 1 linea el tema comun de estas noticias (idioma: {lang}):\nTitulos: {titles[:5]}\nTema:'
        cached = self._check_cache(prompt)
        if cached:
            return cached
        result = self._query(prompt)
        self._save_cache(prompt, result)
        return result

    def summarize_cluster(self, titles, lang='es'):
        titles = self._truncate_titles(titles, 2000)
        prompt = f'''Analiza estas noticias y responde SOLO con JSON:
{{tema: ..., palabras_clave: [...], angulo_editorial: ..., paises_implicados: [...]}}

Titulos: {json.dumps(titles[:8])}
Idioma: {lang}'''
        cached = self._check_cache(prompt)
        if cached:
            return cached if isinstance(cached, dict) else json.loads(cached)
        result = self._query(prompt)
        self._save_cache(prompt, result)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {'tema': result[:100], 'palabras_clave': [], 'angulo_editorial': '', 'paises_implicados': []}

    def detect_editorial_angle(self, article_titles):
        article_titles = self._truncate_titles(article_titles, 1500)
        prompt = f'''Identifica si estas noticias son editoriales coordinados o angulos independientes:
{json.dumps(article_titles)}
Responde SOLO: coordinado, independiente o mixto.'''
        cached = self._check_cache(prompt)
        if cached:
            return cached
        result = self._query(prompt)
        self._save_cache(prompt, result)
        return result

    def classify_stance(self, title, actor):
        prompt = f"Classify the stance toward {actor} in this news headline.\nHeadline: {title[:200]}\nRespond ONLY with one word: pro, contra, or neutral."
        cached = self._check_cache(prompt)
        if cached:
            return cached
        result = self._query(prompt)
        self._save_cache(prompt, result)
        return result

    def _query(self, prompt):
        if self.mode == 'production':
            return self._groq_query(prompt)
        return self._ollama_query(prompt)

    def _groq_query(self, prompt):
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {self.groq_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': self.groq_model,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']

    def _ollama_query(self, prompt):
        try:
            resp = requests.post(
                f'{self.ollama_host}/api/chat',
                json={
                    'model': self.ollama_model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'options': {'temperature': 0.1, 'num_ctx': 2048},
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()['message']['content']
        except requests.Timeout:
            return '(timeout - LLM no disponible)'
        except Exception as e:
            return f'(error: {e})'
