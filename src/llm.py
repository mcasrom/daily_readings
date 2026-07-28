import os
import json
import requests


class LLMProvider:
    def __init__(self, mode='test', groq_model='llama3-70b-8192'):
        self.mode = mode
        self.groq_model = groq_model
        if mode == 'production':
            self.groq_key = os.environ.get('GROQ_API_KEY')
            if not self.groq_key:
                raise ValueError('GROQ_API_KEY no configurada')
        else:
            self.ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
            self.ollama_model = os.environ.get('OLLAMA_LLM_MODEL', 'tinyllama')

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
        return self._query(prompt)

    def summarize_cluster(self, titles, lang='es'):
        titles = self._truncate_titles(titles, 2000)
        prompt = f'''Analiza estas noticias y responde SOLO con JSON:
{{tema: ..., palabras_clave: [...], angulo_editorial: ..., paises_implicados: [...]}}

Titulos: {json.dumps(titles[:8])}
Idioma: {lang}'''
        result = self._query(prompt)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {'tema': result[:100], 'palabras_clave': [], 'angulo_editorial': '', 'paises_implicados': []}

    def detect_editorial_angle(self, article_titles):
        article_titles = self._truncate_titles(article_titles, 1500)
        prompt = f'''Identifica si estas noticias son editoriales coordinados o angulos independientes:
{json.dumps(article_titles)}
Responde SOLO: coordinado, independiente o mixto.'''
        return self._query(prompt)

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
