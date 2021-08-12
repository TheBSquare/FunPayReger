import time
from random import choice
import re
from threading import Thread

from logic.database import Db


def generate_username(length=12):
    db = Db()
    token = db.create_connection()

    years = [x for x in range(1970, 1990)]
    months = [x for x in range(10, 13)]
    days = [x for x in range(10, 28)]

    word = '123456789'
    while len(word) > 8 or len(word) <= 3:
        word = re.sub(r"[`'-/ \\]", '', db.get_random_word(token))

    number = f'{choice(days)}{choice(months)}{choice(years)}'[7 - (11-len(word)):]

    db.close_connection(token)
    return f'{word.capitalize()}{number}'


def generate_email(domain="mail.ru"):
    db = Db()
    token = db.create_connection()

    years = [x for x in range(1970, 1990)]
    months = [x for x in range(10, 13)]
    days = [x for x in range(10, 28)]

    first_name = ""
    while len(first_name) > 8 or len(first_name) <= 3:
        first_name = re.sub(r"[`'-/ \\]", '', db.get_random_word(token)).lower().capitalize()

    last_name = ""
    while len(last_name) > 8 or len(last_name) <= 3:
        last_name = re.sub(r"[`'-/ \\]", '', db.get_random_word(token)).lower().capitalize()

    return f"{first_name}.{last_name}.{choice(months)}{choice(days)}{choice(years)}@{domain}"


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


def run_as_thread(func):
    def wrapper(*args, **kwargs):
        thread = Thread(target=func, args=args, kwargs=kwargs)
        thread.start()

    return wrapper
