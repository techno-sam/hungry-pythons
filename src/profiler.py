import time


class Profiler:
    def __init__(self):
        self.clocks = {}

    def start(self, name):
        self.clocks[name] = time.perf_counter()

    def end(self, name):
        time_between = time.perf_counter() - self.clocks[name]
        del self.clocks[name]
        return time_between
