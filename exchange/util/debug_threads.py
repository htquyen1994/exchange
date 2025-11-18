import threading
import traceback
import sys

_original_start = threading.Thread.start

def debug_start(self, *args, **kwargs):
    # Lấy stack trace nơi gọi Thread.start()
    stack = ''.join(traceback.format_stack())
    print(f"[DEBUG THREAD] Creating new thread: {self.name}", file=sys.stderr)
    print(stack, file=sys.stderr)
    sys.stderr.flush()  # tránh bị mất log

    return _original_start(self, *args, **kwargs)

def patch_threading():
    threading.Thread.start = debug_start
