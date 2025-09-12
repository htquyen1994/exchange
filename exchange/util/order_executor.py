
import threading

def execute_orders_concurrently(primary_func, secondary_func):
    results = [None, None]

    def wrapper(idx, func):
        results[idx] = func()

    t1 = threading.Thread(target=wrapper, args=(0, primary_func))
    t2 = threading.Thread(target=wrapper, args=(1, secondary_func))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    return results[0], results[1]