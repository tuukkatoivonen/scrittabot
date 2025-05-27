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

    def _reset_stats(self):
        self._stats = {
            'model': None,
            'usage': {},
            'timings': {},          # timings not available through LiteLLM
        }

    def __del__(self):
        self._session.close()

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
                for k in self._stats.keys():
                    if k in chunk:
                        self._stats[k] = chunk[k]
            # Lines that are not "data: ..." or empty lines are typically ignored in SSE
            # or could be comments (starting with ':')

    def completion_stats(self):
        return self._stats

    # Doesn't work directly with llama-server (but with LiteLLM)
    def count_tokens(self, messages):
        if isinstance(messages, list):
            section_tokens = len(messages) * 3
            string = ''
            for m in messages:
                string += m['content']
        else:
            # Assume messages is a plain string
            section_tokens = 0
            string = messages
        payload = self._options.copy()
        payload['prompt'] = string
        response = self._session.post(
            self._base_url + '/utils/token_counter',
            json = payload,
            verify = not self._insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['total_tokens'] + section_tokens

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

class LlmLineStreaming(Llm):
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
    import json
    config = json.load(open('config.json', 'r'))
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
    llm = Llm(config['openai_url'], config['openai_key'], options, insecure=True)
    tokens = llm.count_tokens(prompt)
    print(f'Tokens: {tokens}')

    print('-- Llm --')
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
