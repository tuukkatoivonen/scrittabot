from smolagents.local_python_executor import (
    BASE_PYTHON_TOOLS,
    evaluate_python_code,
)

class PythonExecution():
    def __init__(self, tool_list):
        tooldict = {}
        for tool in tool_list:
            for t in tool.tools():
                i = t[0].find('(')
                if i == -1:
                    raise Exception('Badly formatted function description')
                name = t[0][:i]
                if name in tooldict:
                    raise Exception('Tool already defined')
                tooldict[name] = t[1]
        self._tooldict = BASE_PYTHON_TOOLS
        self._tooldict.update(tooldict)
        self._state = {}

    def execute(self, code):
        print(f'EXECUTE: {code}')

        exc = None
        try:
            result, _ = evaluate_python_code(code, self._tooldict, state=self._state)
        except Exception as e:
            exc = e
            print(f'EXCEPTION: {exc}')
        return str(exc) if exc is not None else None
