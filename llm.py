import json
import requests
import urllib3


class Llm:
    def __init__(self, url, api_key=None, options={}, embedding_query='', insecure=False):
        self._base_url = url
        self._api_key = api_key
        self._options = options
        self._insecure = insecure
        if self._insecure:
            urllib3.disable_warnings()
        self._embedding_query = embedding_query

        self._session = requests.Session()
        self._session.headers.update({ "Content-Type": "application/json" })
        if self._api_key:
            self._session.headers.update({ "Authorization": f"Bearer {self._api_key}" })
        self._reset_stats()

        self._tokens_turn = 5           # Tokens consumed by each turn (Gemma3-12)
        self._tokens_image = 259        # Tokens consumed by each image (Gemma3-12)
        self._tokens_m = 1.1139
        self._tokens_b = -26.207

    def __del__(self):
        self._session.close()

    def _reset_stats(self):
        self._stats = {
            'model': None,
            'usage': {},
            'timings': {},          # timings not available through LiteLLM
        }

    def _parse_stats(self, chunk):
        for k in self._stats.keys():
            if k in chunk:
                self._stats[k] = chunk[k]

    def completion(self, messages):
        self._reset_stats()
        payload = self._options.copy()
        payload['messages'] = messages

        response = self._session.post(
            self._base_url + '/v1/chat/completions',
            json = payload,
            verify = not self._insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        response = response.json()
        self._parse_stats(response)

        if ('choices' in response and
            'message' in response['choices'][0] and
            'content' in response['choices'][0]['message']):
            return response['choices'][0]['message']['content']
        raise Exception('API returned bad format')

    def completion_stats(self):
        return self._stats

    # Doesn't work directly with llama-server (but with LiteLLM)
    def count_tokens(self, messages):
        if isinstance(messages, str):
            messages = [{ 'content': messages }]
        tokens = 0
        payload = self._options.copy()
        for m in messages:
            content = m['content']
            if isinstance(content, str):
                content = [{ 'type': 'text', 'text': content }]
            for c in content:
                if c['type'] == 'text':
                    payload['prompt'] = c['text']
                    response = self._session.post(
                        self._base_url + '/utils/token_counter',
                        json = payload,
                        verify = not self._insecure
                    )
                    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                    tokens += response.json()['total_tokens']
                else:
                    # Image
                    tokens += self._tokens_image
            tokens += self._tokens_turn    
        tokens = max(int(tokens * self._tokens_m + self._tokens_b), 1)
        return tokens

    def embedding(self, string):
        payload = self._options.copy()
        payload['input'] = self._embedding_query + string
        response = self._session.post(
            self._base_url + '/v1/embeddings',
            json = payload,
            verify = not self._insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['data'][0]['embedding']

class LlmStreaming(Llm):
    def __init__(self, url, api_key=None, options={}, embedding_query='', insecure=False):
        loc = locals()
        del loc['self']
        del loc['__class__']
        super().__init__(**loc)

    def completion(self, messages):
        self._reset_stats()
        payload = self._options.copy()
        payload['stream'] = True
        payload['stream_options'] = { 'include_usage': True }     # Required for LiteLLM
        payload['messages'] = messages

        response = self._session.post(
            self._base_url + '/v1/chat/completions',
            json = payload,
            stream = True,
            verify = not self._insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        iterator = response.iter_lines()

        for line_bytes in iterator:
            line = line_bytes.decode('utf-8').strip()
            # Standard SSE format: lines start with "data: "
            if line.startswith('data:'):
                data_content = line[len('data:'):].strip()
                if data_content == '[DONE]': # OpenAI-specific end-of-stream marker
                    response.close()
                    return
                chunk = json.loads(data_content)
                if ('choices' in chunk and
                    'delta' in chunk['choices'][0] and
                    'content' in chunk['choices'][0]['delta']):
                    yield chunk['choices'][0]['delta']['content']
                self._parse_stats(chunk)
            # Lines that are not "data: ..." or empty lines are typically ignored in SSE
            # or could be comments (starting with ':')

class LlmLineStreaming(LlmStreaming):
    def __init__(self, url, api_key=None, options={}, embedding_query='', insecure=False):
        loc = locals()
        del loc['self']
        del loc['__class__']
        super().__init__(**loc)

    def completion(self, messages):
        line = None
        for token in super().completion(messages):
            if line is None:
                line = ''
            token_lines = token.split('\n')
            for l in token_lines[:-1]:
                line += l
                yield line
                line = ''
            line += token_lines[-1]
        if line is not None:
            yield line


# Tests
if __name__ == '__main__':
    import yaml
    config = yaml.safe_load(open('config.yaml', 'r'))
    options = {
        'max_tokens': 4096,
        'temperature': 0.0,
        'top_p': 1.0,
        'n': 1,
        'cache_prompt': True,
        'model': config['model_llm'],
    }
    prompt = [
        { 'role': 'system', 'content': 'You are a helpful assistant.' },
        { 'role': 'user', 'content': 'List five animals which can fly.' },
    ]

    print('-- Counting tokens --')
    llm = LlmStreaming(config['openai_url'], config['openai_key'], options, insecure=True)
    tokens = llm.count_tokens(prompt)
    print(f'Tokens: {tokens}')

    print('-- LlmStreaming --')
    comp = llm.completion(prompt)
    for token in comp:
        print(f'<{token}>')
    print(f'Stats: {llm.completion_stats()}')

    print('-- LlmLineStreaming --')
    llm = LlmLineStreaming(config['openai_url'], config['openai_key'], options, insecure=True)
    comp = llm.completion(prompt)
    for token in comp:
        print(f'<{token}>')
    print(f'Stats: {llm.completion_stats()}')
