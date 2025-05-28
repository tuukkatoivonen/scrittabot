#!/usr/bin/env python3

CONFIG_FILE = 'config.json'
EMBEDDING_QUERY = 'Instruct: Given a web search query, retrieve relevant passages that answer the query Query: '
IMAGE_MAX_SIZE = 256

OPTIONS = {
    'max_tokens': 4096,
    'temperature': 0.0,
    'top_p': 1.0,
    'n': 1,
    'cache_prompt': True,
}

import base64
import io
import json
import time
import pprint
from PIL import Image

import context
import llm
import python_execution
import tools
import tool_matrix

class FileHandler():
    def __init__(self, filename, path):
        self._filename = filename
        self._path = path
        self._image = None
        self._max_size = IMAGE_MAX_SIZE
        try:
            self._image = Image.open(path)
        except IOError:
            # Not an image, but regular file
            pass

    def _is_image(self):
        return self._image is not None

    def media_type(self):
        if self._is_image():
            return 'image'
        return 'file'

    def content(self):
        if not self._is_image():
            return f'User sent file: {self._filename}'

        # Scale image to reasonable size and return encoded for LLM
        img = self._image
        if self._image.width > self._max_size or self._image.height > self._max_size:
            scale_width  = self._max_size / self._image.width
            scale_height = self._max_size / self._image.height
            scale = min(scale_width, scale_height)
            new_width = max(int(self._image.width * scale_width), 8)
            new_height = max(int(self._image.height * scale_height), 8)
            img = self._image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Save image to a byte buffer in PNG format
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        # Base64 encode the image bytes
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return 'data:image/png;base64,' + base64_image

class ScrittaBot():
    def __init__(self):
        with open(CONFIG_FILE, 'r') as f:
            self._config = json.load(f)

        options = OPTIONS
        options['model'] = self._config['model_llm']
        self._llm = llm.LlmLineStreaming(self._config['openai_url'], self._config['openai_key'], options, insecure=True)

        self._tools_basic = tools.ToolSetBasic()
        self._tools_system = tools.ToolSetSystem()
        self._tools_matrix = tool_matrix.ToolSetMatrix(self._config)
        self._tool_list = [
            self._tools_basic,
            self._tools_system,
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
        self._context_size = [ 0 ] * 5

    def _run_llm(self):
        msgs = self._context_manager.messages()
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

        self._section_dialogue.add_chunk(content=completion)

        # Check if we're running out of context, and if so, reduce used context
        context_size = self._llm.completion_stats()['usage']['prompt_tokens']
        print(f'RUN LLM context_size:{context_size}')
        self._context_size = self._context_size[1:] + [context_size]
        estimated_increase = 2*max([s[0]-s[1] for s in zip(self._context_size[1:], self._context_size[:-1])])
        print(f'estimated_increase {estimated_increase}')
        estimated_context = context_size + estimated_increase
        while estimated_context > self._config['context_llm'] - 16:
            if not self._context_manager.reduce():
                print('WARNING: Possible context overflow, can not reduce enough')
                break
            estimated_context = self._llm.count_tokens(self._context_manager.messages()) + estimated_increase

        return output

    def run(self):
        while True:
            output = self._run_llm()
            if self._tools_system.shutdown:
                break
            sleep = self._tools_system.get_sleep()
            wake = None
            if sleep is not None and sleep >= 0:
                wake = int(time.time()) + 60*sleep + 1
            while wake is None or int(time.time()) < wake:
                events = 0

                # Check events, break if any
                events += len(output)
                for o in output:
                    self._section_dialogue.add_chunk(service='python', content=o)
                output = []

                matrix_events = self._tools_matrix.get_events()
                events += len(matrix_events)
                for m in matrix_events:
                    extra = f'user="{m["sender"]}"'
                    if not m['filename']:
                        # It is a regular message
                        self._section_dialogue.add_chunk(service='message', extra=extra, content=m['body'])
                    else:
                        extra += f' filename="{m["filename"]}"'
                        fh = FileHandler(m['filename'], self._tools_matrix.get_path(m['filename']))
                        self._section_dialogue.add_chunk(media_type=fh.media_type(), service='message', extra=extra, content=fh.content())

                if events > 0:
                    break
                if sleep is not None and sleep <= 0:
                    break
                time.sleep(1)

scrittabot = ScrittaBot()
scrittabot.run()

# EOF
