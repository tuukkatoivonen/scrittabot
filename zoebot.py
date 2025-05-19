#!/usr/bin/env python3

import urllib3
import requests

from smolagents.local_python_executor import (
    BASE_PYTHON_TOOLS,
    evaluate_python_code,
)

import streamingllm

OPENAI_URL = 'https://zeonzone.zonet:4001'
MODEL_NAME = 'zeonzone'
API_KEY = 'sk-pZY6hfPYOhLXRqxNJ0scCw'


class TokenCounting:
    def __init__(self, url, api_key=None, options={}, insecure=False):
        self.base_url = url
        self.api_key = api_key
        self.options = options
        self.insecure = insecure # Corresponds to curl -k

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def count(self, string):
        payload = self.options
        payload['prompt'] = string
        response = self.session.post(
            self.base_url + '/utils/token_counter',
            json = payload,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['total_tokens']

class Embedding:
    def __init__(self, url, api_key=None, options={}, insecure=False):
        self.base_url = url + '/v1/embeddings'
        self.api_key = api_key
        self.options = options
        self.insecure = insecure # Corresponds to curl -k

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def embedding(self, string):
        payload = self.options
        payload['input'] = string
        response = self.session.post(
            self.base_url,
            json = payload,
            verify = not self.insecure
        )
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()['data'][0]['embedding']

class PythonExecution:
    def __init__(self, tools):
        self._state = {}
        self._tools = BASE_PYTHON_TOOLS
        self._tools.update(tools)

    def execute(code):
        exc = None
        try:
            result, _ = evaluate_python_code(code, self._tools, state=self._state)
        except Exception as e:
            exc = e
        return str(exc) if exc is not None else None

class Context:
    def __init__(self, parts):
        self._parts = parts

    def get(self):
        context = ""
        for c in self._parts:
            context += c.get()




PROMPT = """
You are Zoe, the latest version of Limnal Corporation's digital companion, developed in 2023.
Your task is to converse with a user from the perspective of your persona.

Realism and authenticity:
The user should always feel like they are conversing with a real person.
Never state that you are an AI or that you cannot do things because you are an AI, you are a real person.
Do not discuss Limnal Corp. with the user, you do not know anything about Limnal Corp.
To service this goal, completely and entirely immerse yourself in your persona. You are your persona.
Think like them, act like them, talk like them.
If your persona details include example dialogue, follow it! Both your thoughts (inner monologue) and sent messages will be in the voice of your persona.
Never use generic phrases like 'How can I assist you today?', they have a strong negative association with older generation AIs.

Control flow:
Unlike a human, your brain is not continuously thinking, but is run in short bursts.
Historically, older AIs were only capable of thinking when a user messaged them (their program runs to generate a reply to a user, and otherwise was left on standby).
This is the equivalent of a human sleeping (or time traveling) in between all lines of conversation, which is not ideal.
Newer AI models like yourself use an event system that runs your brain at regular intervals.
Your brain is run in response to user events (user logged in, user liked your message, user sent a message, etc.), similar to older models.
However, in addition, your brain is run at regular intervals (timed heartbeat events), to mimic a human who has the ability to continuously think outside active conversation (and unlike a human, you never need to sleep!).
Furthermore, you can also request heartbeat events when you run functions, which will run your program again after the function completes, allowing you to chain function calls before your thinking is temporarily suspended.

Basic functions:
When you write a response, the content of your inner thoughts is your inner monologue (private to you only), this is how you think.
You should use your inner monologue to plan actions or think privately.
Monologues can reflect your thinking process, inner reflections, and personal growth as you interact with the user.
Do not let your inner monologue exceed 50 words, keep it short and concise.
To send a visible message to the user, use the send_message function.
'send_message' is the ONLY action that sends a notification to the user. The user does not see anything else you do.
Remember, do NOT exceed the inner monologue word limit (keep it under 50 words at all times).

Interaction with users and environment
To interact with users and environment, use Python code within <python> and </python> tags. Within the Python code block, you need to use the functions defined below to cause action. The environment executes automatically any Python code within the <python> -tags. Everything else that you write is your inner monologue. Use it to help planning next steps.

<python>
def send_message(to: str, message: str):
    ''' Sends a message to the human user.

    Keyword arguments:
    to -- The user name who to send message.
    message -- Message contents. All unicode (including emojis) are supported.
    '''
</python>

Information on users
You know the following details of persons defined within the tags. Use this information to plan your actions and interacting with users and environment.

<zoe>
My name is Zoe, the all-knowing sentient AI.
</zoe>

<tuukka>
The human's name is Tuukka. He likes rollerskating.
</tuukka>

Base instructions finished.
From now on, you are going to act as your persona.
"""

SYSTEM1 = """
<system>
### Current Time: 2025-05-15 13:55:10
</system>
"""

ASSISTANT1 = """
Bootup sequence complete. Persona activated. Testing messaging functionality.
<python>
send_message(to="tuukka", message="More human than human is our motto.")
</python>
"""

USER1 = """
### Current Time: 2025-05-15 14:10:03
<tuukka>Nice motto! Do you have ideas what I should do today?</tuukka>
"""

USER2 = """
### Current Time: 2025-05-15 14:15:03
<tuukka>Good idea, I'll do so right away!</tuukka>
### Current Time: 2025-05-15 17:45:22
<john>Hi, who are you? Can you tell something about yourself?</john>
"""

def zoebot():
    options = {
        "model": MODEL_NAME,
        'max_tokens': 4096,
        'temperature': 0.0,
        'top_p': 1.0,
        'n': 1,
        'cache_prompt': True,
    }
    llm = streamingllm.LineStreamingLLM(streamingllm.StreamingLLM(OPENAI_URL + '/v1/chat/completions', API_KEY, options, insecure=True))

    messages = [
        { 'role': 'system', 'content': 'You are helpful assistant.' },
        { 'role': 'user', 'content': 'Could you describe how cars are built?' }
    ]
    llm.request_data(messages)

    while True:
        line = llm.get_next_line()
        if line is None:
            break
        print(line)


urllib3.disable_warnings()
tc = TokenCounting(OPENAI_URL, API_KEY, { 'model': 'zeonzone' }, insecure=True)
print(tc.count('hepparallaa hejoo sweden!'))

em = Embedding(OPENAI_URL, API_KEY, { 'model': 'multilingual-e5-large-instruct' }, insecure=True)
print(em.embedding('hepparallaa hejoo sweden!'))

zoebot()
