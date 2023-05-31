import dukpy


class JSContext:
    def __init__(self):
        self.interp = dukpy.JSInterpreter()
        # export js functions to corresponding python functions
        self.interp.export_function("log", print)

        with open("Sheets/runtime.js") as f:
            self.interp.evaljs(f.read())

    def run(self, code):
        return self.interp.evaljs(code)
