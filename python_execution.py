from functools import partial

from smolagents.local_python_executor import (
    BASE_PYTHON_TOOLS,
    evaluate_python_code,
)

import context

class PythonExecution(context.Section):
    def __init__(self):
        make_note = partial(self._make_note)
        replace_note = partial(self._replace_note)
        search_note = partial(self._search_note)
        send_message = partial(self._send_message)
        increase_mood = partial(self._increase_mood)
        decrease_mood = partial(self._decrease_mood)
        add_goal = partial(self._add_goal)
        delete_goal = partial(self._delete_goal)
        search_document = partial(self._search_document)

        tools = {
            'make_note': make_note,
            'replace_note': replace_note,
            'search_note': search_note,
            'send_message': send_message,
            'increase_mood': increase_mood,
            'decrease_mood': decrease_mood,
            'add_goal': add_goal,
            'delete_goal': delete_goal,
            'search_document': search_document,
        }        

        self._tools = BASE_PYTHON_TOOLS
        self._tools.update(tools)
        self._state = {}

    def content(self):
        return [[ 'system', self._get_prompt() + '\n' ]]

    def execute(self, code):
        print(f'EXECUTE: {code}')

        exc = None
        try:
            result, _ = evaluate_python_code(code, self._tools, state=self._state)
        except Exception as e:
            exc = e
            print(f'EXCEPTION: {exc}')
        return str(exc) if exc is not None else None

    def _make_note(self, summary: str, keywords: list[str]):
        print('make_note')

    def _replace_note(self, ref: str, summary: str = None, keywords: list[str] = None):
        print('replace_note')

    def _search_note(self, keywords: list[str] = None, summary_contains: str = None, date_from: str = None, date_to: str = None):
        print('search_note')

    def _send_message(self, user: str, message: str):
        print('send_message')

    def _increase_mood(self, mood_name: str):
        print('increase_mood')

    def _decrease_mood(self, mood_name: str):
        print('decrease_mood')

    def _add_goal(self, goal_description: str):
        print('add_goal')

    def _delete_goal(self, goal_index: int):
        print('delete_goal')

    def _search_document(self, document_name: str, query: str):
        print('search_document')


    def _get_prompt(self):
        return '''## Functions

These special function are available for you to help advancing your goals.

```python

def make_note(summary: str, keywords: list[str]):
    """
    Creates a new note with a summary and keywords.
    The summary should be a concise description of the information.
    Keywords help in retrieving the note later.
    Example: make_note(summary='User Bob enjoys jazz music from the 1950s', keywords=['bob', 'music', 'jazz', '1950s'])
    """

def replace_note(ref: str, summary: str = None, keywords: list[str] = None):
    """
    Updates an existing note identified by its reference ID (ref).
    Provide a new summary and/or keywords to update them.
    To delete the note entirely, call with only ref and summary=None.
    Example (update): replace_note(ref='123', summary='User Bob likes classical and jazz music')
    Example (delete): replace_note(ref='123', summary=None)
    """

def search_note(keywords: list[str] = None, summary_contains: str = None, date_from: str = None, date_to: str = None):
    """
    Searches for notes. You can search by keywords, text within the summary, or date range.
    Example: search_note(keywords=['bob', 'music'])
    """

def send_message(user: str, message: str):
    """
    Sends a message to the specified user. This is the only way to communicate with users.
    Example: send_message(user='bob', message='Hello Bob, how are you today?')
    """

def increase_mood(mood_name: str):
    """
    Increases the specified mood (e.g., 'happy') by a small amount.
    Mood names are: 'sad', 'happy', 'afraid', 'angry', 'surprised', 'disgusted'.
    Example: increase_mood(mood_name='happy')
    """

def decrease_mood(mood_name: str):
    """
    Decreases the specified mood (e.g., 'sad') by a small amount.
    Example: decrease_mood(mood_name='sad')
    """

def add_goal(goal_description: str):
    """
    Adds a new goal to your list of goals.
    Example: add_goal(goal_description="Find out user Alice's favorite color")
    """

def delete_goal(goal_index: int):
    """
    Deletes a goal from your list using its numerical index.
    Example: delete_goal(goal_index=2)
    """

def search_document(document_name: str, query: str):
    """
    Searches for information within a specified document (e.g., 'faq.txt', 'manual.pdf').
    Returns relevant text snippets from the document.
    Example: search_document(name='user_manual.txt', query='how to reset device')
    """
```
'''
