#!/usr/bin/env python3

CONFIG_FILE = 'config.json'
EMBEDDING_QUERY = 'Instruct: Given a web search query, retrieve relevant passages that answer the query Query: '

OPTIONS = {
    'max_tokens': 4096,
    'temperature': 0.0,
    'top_p': 1.0,
    'n': 1,
    'cache_prompt': True,
}

import json
import time
import pprint

import context
import llm
import python_execution
import tools
import tool_matrix

class ScrittaBot():
    def __init__(self):
        with open(CONFIG_FILE, 'r') as f:
            self._config = json.load(f)

        options = OPTIONS
        options['model'] = self._config['model_llm']
        self._llm = llm.LlmLineStreaming(self._config['openai_url'], self._config['openai_key'], options, insecure=True)

        self._tools_basic = tools.ToolSetBasic()
        self._tools_sleep = tools.ToolSetSleep()
        self._tools_matrix = tool_matrix.ToolSetMatrix(self._config)
        self._tool_list = [
            self._tools_basic,
            self._tools_sleep,
            self._tools_matrix,
        ]
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

    def _run_llm(self):
        msgs = self._messages()
        #pprint.pp(msgs)
        print(f'RUN LLM dialogue:{len(msgs)}')
        comp = self._llm.completion(msgs)
        in_python = False
        completion = ''
        output = []
        for line in comp:
            print(line)
            completion += line + '\n'
            line_strip = line.strip()
            if line_strip == '```' and in_python:
                in_python = False
                out = self._python_execution.execute(python)
                if out:
                    output.append(out)
            if in_python:
                python += line + '\n'
            if line_strip == '```python':
                in_python = True
                python = ''
        self._section_dialogue.add_chunk(None, completion)
        return output

    def run(self):
        while True:
            output = self._run_llm()
            sleep = self._tools_sleep.get_sleep()
            wake = None
            if sleep is not None and sleep >= 0:
                wake = int(time.time()) + 60*sleep + 1
            while wake is None or int(time.time()) < wake:
                events = 0

                # Check events, break if any
                events += len(output)
                for o in output:
                    self._section_dialogue.add_chunk('output', o)
                output = []

                matrix_events = self._tools_matrix.get_events()
                events += len(matrix_events)
                for m in matrix_events:
                    self._section_dialogue.add_chunk('message', m['body'], extra=f'user="{m["sender"]}"')

                if events > 0:
                    break
                if sleep is not None and sleep <= 0:
                    break
                time.sleep(1)

scrittabot = ScrittaBot()
scrittabot.run()

# EOF
