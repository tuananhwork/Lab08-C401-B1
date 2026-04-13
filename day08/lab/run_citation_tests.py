import importlib
import traceback

module = importlib.import_module('test_rag_citation')

for name in dir(module):
    if name.startswith('test_'):
        func = getattr(module, name)
        try:
            func()
            print(f"{name}: PASS")
        except AssertionError as e:
            print(f"{name}: FAIL - AssertionError: {e}")
        except Exception as e:
            print(f"{name}: FAIL - {type(e).__name__}: {e}")
            traceback.print_exc()
