import time
from logic.registration import Email, Account, RegistrationManager, Proxy
from logic.utils import generate_username
from logic.database import Db
from threading import Thread
from datetime import datetime
from secret import proxy


def account_checker(accounts):
    temp = {}
    total = len(accounts)
    print(f'Total: {total}')
    while not stop:
        for account in accounts:
            if not account.steps["working"]["status"]:
                if account in temp:
                    last_key = list(account.steps.keys())[-1]
                    s = f'{temp[account]["number"]}.{datetime.fromtimestamp(time.time()).strftime("%m/%d/%Y, %H:%M:%S")}' \
                        f'{account.email.email} - {account.username} - {account.password} - {last_key} - {account.steps[last_key]}'

                    with open("logs.txt", 'a') as f:
                        f.write(s)
                        f.close()
                    print(s)
                    del temp[account]
                continue
            elif account not in temp:
                temp[account] = {"number": total}
                total -= 1

            for step_key in account.steps.copy():
                if step_key not in temp[account] or account.steps[step_key]["status"] != temp[account][step_key]["status"]:
                    temp[account][step_key] = account.steps[step_key]
                    s = f'{temp[account]["number"]}. {datetime.fromtimestamp(time.time()).strftime("%m/%d/%Y, %H:%M:%S")} - ' \
                        f'{account.email.email} - {account.username} - {account.password} - {step_key} - {temp[account][step_key]}'
                    with open("logs.txt", 'a') as f:
                        f.write(s)
                        f.close()
                    print(s)


def main():
    with open("email.txt", 'r') as f:
        mails = [data.replace('\n', '').split(':') for data in f.readlines()]
        f.close()

    accounts = []
    db = Db()
    token = db.create_connection()
    for mail in mails:

        email_name, password = mail

        email = Email(email=email_name, domain="mail.ru", password=password)

        account = Account(username=generate_username(), password=email.password, email=email, proxy=proxy)

        account_data = db.check_account(account, token)

        if account_data is None:
            accounts.append(account)
            db.add_account(account, token)

        elif account_data["status"] == 0:
            account.username = account_data["account"].username
            account.password = account_data["account"].password
            accounts.append(account)

    db.commit_connection(token)
    db.close_connection(token)

    thread = Thread(target=account_checker, args=(accounts, ))
    thread.start()

    manager = RegistrationManager(accounts=accounts, db=db)
    manager.start_registration(2)


if __name__ == '__main__':
    stop = False
    #os.chmod(driver_path, 755)
    main()