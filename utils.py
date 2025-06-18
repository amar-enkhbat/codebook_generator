import time

def perf_sleep(t: float):
    t1 = time.perf_counter() + t
    while time.perf_counter() <= t1:
        pass
