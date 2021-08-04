from threading import Lock


class SingletonMeta(type):
    instances = {}

    lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls.lock:
            if cls not in cls.instances:
                instance = super().__call__(*args, **kwargs)
                cls.instances[cls] = instance
        return cls.instances[cls]
