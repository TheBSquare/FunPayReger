import time


def step(func):
    def wrapper(self, step_name, **kwargs):
        self.steps[step_name] = {"status": "loading"}
        t1 = time.time()
        try:
            data = func(self, **kwargs)
            self.steps[step_name] = {"status": "ok"}
            self.steps[step_name].update(data)
            self.steps[step_name]["elapsed"] = time.time() - t1
            return self.steps[step_name]
        except Exception as err:
            self.steps[step_name] = {"status": "error", "description": str(err)}
            self.steps[step_name]["elapsed"] = time.time() - t1
            self.steps["working"]["status"] = "error"
            return self.steps[step_name]
    return wrapper
