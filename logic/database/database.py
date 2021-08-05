import sqlite3

from logic.registration import Email, Account
from settings import database_path
from .singleton import SingletonMeta
from uuid import uuid4


class Db(metaclass=SingletonMeta):
    connections = {}

    def __init__(self):
        token = self.create_connection()
        self.create_accounts_table(token)
        self.commit_connection(token)
        self.close_connection(token)

    def create_accounts_table(self, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS accounts(email text, username text, password text, status int)")
        cursor.close()

    def get_random_word(self, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM words ORDER BY RANDOM() LIMIT 1")
        data = cursor.fetchone()
        cursor.close()
        return data[0]

    def get_accounts(self, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("SELECT email, username, password, status FROM accounts")
        data = cursor.fetchall()
        cursor.close()

        for row in data:
            email = Email(email=row[0], domain='mail.ru', password=row[2])
            account = Account(username=row[1], password=email.password, email=email)

            yield {"account": account, "status": row[-1]}

    def update_account(self, account, status, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("UPDATE accounts SET status = ? WHERE email=?", (status, account.email.email))
        cursor.close()

    def check_account(self, account, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("SELECT email, username, password, status FROM accounts WHERE email=?", (account.email.email, ))
        data = cursor.fetchone()
        cursor.close()

        if not data is None:
            email_name, domain = data[0].split("@")

            email = Email(email=email_name, domain=domain, password=data[2])
            account = Account(username=data[1], password=email.password, email=email)

            return {"account": account, "status": data[-1]}

    def add_account(self, account, token):
        connection = self.connections[token]
        cursor = connection.cursor()
        cursor.execute("SELECT status FROM accounts WHERE email=?", (account.email.email,))
        data = cursor.fetchone()
        if data is None:
            cursor.execute("INSERT INTO accounts(email, username, password, status) VALUES(?, ?, ?, 0)", (account.email.email, account.username, account.password))
        cursor.close()

    def commit_connection(self, token):
        self.connections[token].commit()

    def create_connection(self):
        token = uuid4()
        self.connections[token] = sqlite3.connect(database_path)
        return token

    def close_connection(self, token):
        self.connections[token].close()
        del self.connections[token]


if __name__ == '__main__':
    pass
