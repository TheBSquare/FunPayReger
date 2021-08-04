from random import choice
import re

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
