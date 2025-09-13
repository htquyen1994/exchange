import threading
import traceback

def execute_orders_concurrently(primary_func, secondary_func):
    results = [None, None]
    errors = [None, None]
    def wrapper(idx, func):
        try:
            results[idx] = func()
        except Exception as e:
            errors[idx] = e
            traceback.print_exc()  # in ra stacktrace, hoặc log lại

    t1 = threading.Thread(target=wrapper, args=(0, primary_func))
    t2 = threading.Thread(target=wrapper, args=(1, secondary_func))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if errors[0]:
        raise errors[0]
    if errors[1]:
        raise errors[1]

    return results[0], results[1]