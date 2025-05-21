#!/usr/bin/env python3

OPENAI_URL = 'https://zeonzone.zonet:4001'
MODEL_LLM = 'zeonzone'
MODEL_EMBEDDING = 'multilingual-e5-large-instruct'
EMBEDDING_QUERY = 'Instruct: Given a web search query, retrieve relevant passages that answer the query Query: '
API_KEY = 'sk-pZY6hfPYOhLXRqxNJ0scCw'

OPTIONS = {
    'max_tokens': 4096,
    'temperature': 0.0,
    'top_p': 1.0,
    'n': 1,
    'cache_prompt': True,
}

import pprint

import context
import llm
import python_execution
import tools

class ZoeBot():
    def __init__(self):
        options = OPTIONS
        options['model'] = MODEL_LLM
        self._llm = llm.LlmLineStreaming(OPENAI_URL, API_KEY, options, insecure=True)

        self._tool_list = [ tools.ToolSetBasic() ]

        self._python_execution = python_execution.PythonExecution(self._tool_list)
        self._section_instructions = context.SectionInstructions()
        self._section_tools = context.SectionTools(self._tool_list)
        self._section_mood = context.SectionMood()
        self._section_goals = context.SectionGoals()
        self._section_dialogue = context.SectionDialogue()

        self._context_manager = context.ContextManager([
            self._section_instructions,
            self._section_tools,
            self._section_mood,
            self._section_goals,
            self._section_dialogue,
        ])

    def _messages(self):
        msgs = []
        context = self._context_manager.content()
        for c in context:
            msgs.append({ 'role': c[0], 'content': c[1] })
        return msgs

    def run(self):
        msgs = self._messages()
        #pprint.pp(msgs)
        comp = self._llm.completion(msgs)
        in_python = False
        for line in comp:
            print(line)
            line_strip = line.strip()
            if line_strip == '```' and in_python:
                in_python = False
                self._python_execution.execute(python)
            if in_python:
                python += line + '\n'
            if line_strip == '```python':
                in_python = True
                python = ''

tc = llm.Llm(OPENAI_URL, API_KEY, { 'model': MODEL_LLM }, insecure=True)
print(tc.count_tokens('hepparallaa hejoo sweden!'))

em = llm.Llm(OPENAI_URL, API_KEY, { 'model': MODEL_EMBEDDING }, embedding_query=EMBEDDING_QUERY, insecure=True)
print(em.embedding('hepparallaa hejoo sweden!'))

zoebot = ZoeBot()
zoebot.run()

# EOF
