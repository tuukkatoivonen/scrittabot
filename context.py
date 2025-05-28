import datetime

import system_prompt

def get_time():
    """
    Returns the current time as a string in 'YYYY-MM-DD HH:MM:SS' format.
    """
    now = datetime.datetime.now()  # Get the current date and time
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time

class Section:
    def __init__(self):
        self._max_tokens = 10000000

    def content(self):
        # Returns a list of tuples of (media_type, role, open_tag, close_tag, content)
        # Where
        # - media_type: 'text' / 'image' / 'file'
        # - role: 'assistant': generated (or pretended to be generated) by LLM
        #         'user': anything else
        raise Exception('no content in base class')

    def set_max_tokens(self, tokens):
        self._max_tokens = tokens

    def reduce(self):
        # Reduce required context space. Returns True if successful, False otherwise
        return False

class SectionInstructions(Section):
    def content(self):
        return [( 'text', 'system', '', '', system_prompt.SYSTEM_PROMPT + '\n' )]

class SectionTools(Section):
    def __init__(self, tool_list):
        super().__init__()
        self._tool_list = tool_list

    def content(self):
        prompt = '## Functions\n\nThese special functions are available for you to help to advance your goals.\n\n```python\n'
        for tool in self._tool_list:
            for t in tool.tools():
                prompt += 'def ' + t[0] + '\n'
        prompt += '```\n\n'
        return [( 'text', 'system', '', '', prompt )]

class SectionMood(Section):
    def __init__(self):
        super().__init__()
        self._mood = {
            'sad': 0.0,
            'happy': 0.5,
            'afraid': 0.0,
            'angry': 0.0,
            'surprised': 0.3,
            'disgusted': 0.0,
        }
        self._step = 0.2

    def _text(self, amount):
        if amount <= 0.2:
            return 'not at all'
        elif 0.2 < amount <= 0.4:
            return 'slightly'
        elif 0.4 < amount <= 0.6:
            return 'moderately'
        elif 0.6 < amount <= 0.8:
            return 'very'
        elif 0.8 < amount:
            return 'extremely'

    def increase_mood(self, mood_name):
        self._mood[mood_name] += self._step
        if self._mood[mood_name] > 1.0:
            self._mood[mood_name] = 1.0

    def decrease_mood(self, mood_name):
        self._mood[mood_name] -= self._step
        if self._mood[mood_name] < 0.0:
            self._mood[mood_name] = 0.0

    def content(self):
        s = '# Your mood is now:\n\n'
        for mood, amount in self._mood.items():
            s += f'- {mood}: {self._text(amount)}\n'
        return [( 'text', 'system', '', '', s + '\n' )]

class SectionGoals(Section):
    def __init__(self):
        super().__init__()
        self._goals = [
            'Collect information on important facts and make notes of them',
            'Keep people happy',
        ]

    def add_goal(description):
        self._goals.insert(0, description)

    def delete_goal(index):
        self._goals.pop(index-1)

    def content(self):
        s = '# Goals\n\nYou have decided to advance the following goals:\n\n'
        for i, g in enumerate(self._goals):
            s += f'{i+1}. {g}\n'
        return [( 'text', 'system', '', '', s + '\n' )]

class SectionDialogue(Section):
    def __init__(self):
        super().__init__()
        self._chunks = []
        self.add_chunk(service='system', content='Bootup sequence complete. Persona activated.')
        self.add_chunk(content="Let's first test if Python code execution works.\n```python\nx = 1 + 2\nprint(x)\n```")
        self.add_chunk(service='python', content='3')

    def add_chunk(self, media_type='text', service=None, extra='', content=None):
        # - service: None: LLM generated, role is 'assistant'; role for everything else is 'user'
        #            'system': system generated messages
        #            'python': Output from the Python executor.
        #            'note': A note fetched from the RAG database.
        #            'message': User sent a message.
        print(f'ADD_CHUNK(media_type="{media_type}", service="{service}", extra="{extra}", content="{content if content is None or len(content)<256 else '...'}")')
        if media_type == 'text' and content == '':
            raise Exception('Empty text content')
        if extra:
            extra = ' ' + extra.strip()
        extra += f' time="{get_time()}"'
        if media_type == 'file':            # For now, no special support for files
            media_type = 'text'
        open_tag, close_tag = ('', '')
        if service:
            role = 'user'
            open_tag = f'<{service}{extra}>'
            close_tag = f'</{service}>\n'
        else:
            role = 'assistant'
        self._chunks.append(( media_type, role, open_tag, close_tag, content ))

    def content(self):
        # Returns a list of tuples of (media_type, role, open_tag, close_tag, content)
        return self._chunks

    def reduce(self):
        # Reduce required context space
        if len(self._chunks) > 5:
            print('SectionDialogue: reducing')
            while True:
                del self._chunks[0]
                if self._chunks[0][1] == 'user':        # First chunk must have role 'user'
                    break
            return True
        return False


class ContextManager():
    def __init__(self, sections):
        super().__init__()
        self._sections = sections

    def messages(self):
        messages = [{ 'role': 'system', 'content': '' }]
        last_role = messages[0]['role']
        for section in self._sections:
            for chunk in section.content():
                # Determine role
                role = chunk[1]
                if last_role!='system' and role=='system':
                    raise Exception('All system messages must be first')

                # Determine new content by media_type
                was_str = isinstance(messages[-1]['content'], str)
                if chunk[0] == 'text':
                    content = chunk[2] + chunk[4] + chunk[3]        # A plain string
                    is_str = True
                elif chunk[0] == 'image':
                    content = [{ 'type': 'image_url', 'image_url': {'url':chunk[4]} }]
                    is_str = False
                else:
                    raise Exception('Only text and images supported for now')

                if last_role==role:
                    # Merge into previous message
                    if is_str != was_str:
                        # Convert content to list
                        if was_str:
                            messages[-1]['content'] = [{ 'type': 'text', 'text': messages[-1]['content'] }]
                        if is_str:
                            content = [{ 'type': 'text', 'text': content }]
                    messages[-1]['content'] += content
                else:
                    # A new message
                    messages.append({ 'role': role, 'content': content })
                last_role = role
        # Last message must always be from user, otherwise LLM returns empty string. FIXME: better handling
        if messages[-1]['role'] != 'user':
            messages.append({ 'role': 'user', 'content': f'<system time="{get_time()}"></system>\n' })
        return messages

    def reduce(self):
        for s in reversed(self._sections):
            r = s.reduce()
            if r:
                return True
        return False

