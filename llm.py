import json
import requests
import urllib3


class Llm:
    def __init__(self, url, api_key=None, options={}, embedding_query='', insecure=False):
        self.base_url = url
        self.api_key = api_key
        self.options = options
        self.insecure = insecure
        if self.insecure:
            urllib3.disable_warnings()
        self.embedding_query = embedding_query

        self.session = requests.Session()
        self.session.headers.update({ "Content-Type": "application/json" })
        if self.api_key:
            self.session.headers.update({ "Authorization": f"Bearer {self.api_key}" })

    def __del__(self):
        self.session.close()

    def completion(self, messages):
        payload = self.options
        payload['stream'] = True
        payload['messages'] = messages

        response = self.session.post(
            self.base_url + '/v1/chat/completions',
            json = payload,
            stream = True,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        iterator = response.iter_lines()

        for line_bytes in iterator:
            line = line_bytes.decode('utf-8').strip()
            # Standard SSE format: lines start with "data: "
            if line.startswith("data:"):
                data_content = line[len('data:'):].strip()
                if data_content == '[DONE]': # OpenAI-specific end-of-stream marker
                    response.close()
                    return
                chunk_json = json.loads(data_content)
                delta = chunk_json['choices'][0]['delta']
                if 'content' in delta:
                    yield delta['content']
            # Lines that are not "data: ..." or empty lines are typically ignored in SSE
            # or could be comments (starting with ':')

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
        payload = self.options
        payload['prompt'] = string
        response = self.session.post(
            self.base_url + '/utils/token_counter',
            json = payload,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['total_tokens'] + section_tokens

    def embedding(self, string):
        payload = self.options
        payload['input'] = self.embedding_query + string
        response = self.session.post(
            self.base_url + '/v1/embeddings',
            json = payload,
            verify = not self.insecure
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

    print('-- LlmLineStreaming --')
    llm = LlmLineStreaming(config['openai_url'], config['openai_key'], options, insecure=True)
    comp = llm.completion(prompt)
    for token in comp:
        print(f'<{token}>')
