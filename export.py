from logic.database import Db


def main():
    db = Db()
    token = db.create_connection()

    with open("account.txt", "a") as f:
        for account_data in db.get_accounts(token):
            account = account_data["account"]
            status = account_data["status"]
            if status > 0:
                db.update_account(account, status=-1, token=token)
                f.write(f'{account.email.full_mail};{account.username};{account.password}\n')
        f.close()

    db.commit_connection(token)
    db.close_connection(token)


if __name__ == '__main__':
    main()
