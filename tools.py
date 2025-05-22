from typing import Optional

class ToolSetBasic():
    def __init__(self):
        self._print = self.default_print

    def default_print(self, s):
        print(s)

    def set_print(self, p):
        self._print = p

    def tools(self):
        return [
('''make_note(summary: str, keywords: list[str]):
    """
    Creates a new note with a summary and keywords.
    The summary should be a concise description of the information.
    Keywords help in retrieving the note later.
    Example: make_note(summary='User Bob enjoys jazz music from the 1950s', keywords=['bob', 'music', 'jazz', '1950s'])
    """
''', self._make_note),

('''replace_note(ref: str, summary: str = None, keywords: list[str] = None):
    """
    Updates an existing note identified by its reference ID (ref).
    Provide a new summary and/or keywords to update them.
    To delete the note entirely, call with only ref and summary=None.
    Example (update): replace_note(ref='123', summary='User Bob likes classical and jazz music')
    Example (delete): replace_note(ref='123', summary=None)
    """
''', self._replace_note),

('''search_note(keywords: list[str] = None, summary_contains: str = None, date_from: str = None, date_to: str = None):
    """
    Searches for notes. You can search by keywords, text within the summary, or date range.
    Example: search_note(keywords=['bob', 'music'])
    """
''', self._search_note),

('''send_message(user: str, message: str):
    """
    Sends a message to the specified user. This is the only way to communicate with users.
    Example: send_message(user='bob', message='Hello Bob, how are you today?')
    """
''', self._send_message),

('''increase_mood(mood_name: str):
    """
    Increases the specified mood (e.g., 'happy') by a small amount.
    Mood names are: 'sad', 'happy', 'afraid', 'angry', 'surprised', 'disgusted'.
    Example: increase_mood(mood_name='happy')
    """
''', self._increase_mood),

('''decrease_mood(mood_name: str):
    """
    Decreases the specified mood (e.g., 'sad') by a small amount.
    Example: decrease_mood(mood_name='sad')
    """
''', self._decrease_mood),

('''add_goal(goal_description: str):
    """
    Adds a new goal to your list of goals.
    Example: add_goal(goal_description="Find out user Alice's favorite color")
    """
''', self._add_goal),

('''delete_goal(goal_index: int):
    """
    Deletes a goal from your list using its numerical index.
    Example: delete_goal(goal_index=2)
    """
''', self._delete_goal),

('''search_document(document_name: str, query: str):
    """
    Searches for information within a specified document (e.g., 'faq.txt', 'manual.pdf').
    Returns relevant text snippets from the document.
    Example: search_document(name='user_manual.txt', query='how to reset device')
    """
''', self._search_document),
        ]

    def _make_note(self, summary: str, keywords: list[str]):
        print('make_note')

    def _replace_note(self, ref: str, summary: str = None, keywords: list[str] = None):
        print('replace_note')

    def _search_note(self, keywords: list[str] = None, summary_contains: str = None, date_from: str = None, date_to: str = None):
        print('search_note')
        self._print('No notes available')

    def _send_message(self, user: str, message: str):
        print('send_message')
        self._print('Unknown user')

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
        self._print('Document not found')


class ToolSetSleep(ToolSetBasic):
    def __init__(self):
        super().__init__()
        self._set_sleep = -1    # -1: do not sleep but return immediately to processing

    def tools(self):
        return [
('''sleep(min_time: Optional[int]):
    """
    Suspends AI from running and thinking for a minimum of 'min_time' minutes or
    until a system event is received (such as an user message), whichever occurs sooner.
    AI should call always this function when there are no more actions that it could take
    to advance its goals. If optional 'min_time' is not given, sleep until next system event.
    Example: sleep()
    """
''', self._sleep),
        ]

    def get_sleep(self):
        s = self._set_sleep
        self._set_sleep = -1
        return s

    def _sleep(min_time: Optional[int] = None):
        self._set_sleep = min_time
        print(f'sleep {min_time}')

