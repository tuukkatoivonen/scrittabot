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
        return [[ 'system', '' ]]

    def set_max_tokens(self, tokens):
        self._max_tokens = tokens

class SectionInstructions(Section):
    def content(self):
        return [[ 'system', system_prompt.SYSTEM_PROMPT + '\n' ]]

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
        return [[ 'system', prompt ]]

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
        return [[ 'system', s + '\n' ]]

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
        return [[ 'system', s + '\n' ]]

class SectionDialogue(Section):
    def __init__(self):
        super().__init__()
        turn1 = f'<system time="{get_time()}">\nBootup sequence complete. Persona activated.\n</system>'
        turn2 = "Let's first test if Python code execution works.\n```python\nx = 1 + 2\nprint(x)\n```"
        turn3 = f'<output time="{get_time()}">\n3\n</output>'
        self._chunks = [
            [ 'user', turn1 ],
            [ 'assistant', turn2 ],
            [ 'user', turn3 ],
        ]

    def add_chunk(role, content):
        self._chunks.append([ role, content ])

    def content(self):
        return self._chunks

class ContextManager(Section):
    def __init__(self, sections):
        super().__init__()
        self._sections = sections

    def content(self):
        cont = []
        for section in self._sections:
            for chunk in section.content():
                if len(cont) > 0 and chunk[0] == cont[-1][0]:
                    cont[-1][1] += chunk[1]
                else:
                    cont.append(chunk)
        return cont
