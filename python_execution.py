from smolagents.local_python_executor import (
    BASE_PYTHON_TOOLS,
    evaluate_python_code,
)

class PythonExecution():
    def __init__(self, tool_list):
        self._state = {}
        tooldict = {}
        for tool in tool_list:
            tool.set_print(self._custom_print)
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

    def _custom_print(self, s):
        self._state["_print_outputs"].value += s

    def execute(self, code):
        print(f'EXECUTE: {code}')

        try:
            result, _ = evaluate_python_code(code, self._tooldict, state=self._state)
        except Exception as e:
            print(f'EXCEPTION: {e}')
            self._custom_print(str(e))
        return self._state["_print_outputs"].value
