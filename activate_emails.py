from threading import Thread

import time
from datetime import datetime
from logic.registration import Email
from logic.registration.managers import MailRuManager
from settings import email_logs


def account_checker(accounts):
    temp = {}
    total = len(accounts)
    print(f'Total: {total}')

    with open(email_logs, 'w+') as f:
        f.close()

    while not stop:
        for account in accounts:
            if account.email in temp:
                for step_key in account.steps.copy():
                    if step_key not in temp[account.email] or account.steps[step_key]["status"] != temp[account.email][step_key]["status"]:
                        temp[account.email][step_key] = account.steps[step_key]
                        s = f'{temp[account.email]["number"]}.{datetime.now().strftime("%m/%d/%Y-%H:%M.%S")} - ' \
                            f'{account.email} - {account.password} - {step_key} - {temp[account.email][step_key]}'
                        with open(email_logs, 'a', encoding="UTF-8") as f:
                            f.write(f'{s}\n')
                            f.close()
                        print(s)

                if account.steps["working"]["status"] == "error" or account.steps["working"]["status"] == "finished":
                    del temp[account.email]

            else:
                if account.steps["working"]["status"] == "waiting":
                    pass
                elif account.steps["working"]["status"] == 'ok' and account.email not in temp:
                    temp[account.email] = {"number": total}
                    total -= 1


def main():
    global stop

    with open("email.txt", "r") as f:
        rows = [row.replace("\n", '').split(":") for row in f.readlines()]

    emails = [Email(email=row[0], password=row[1], domain="mail.ru") for row in rows]

    thread = Thread(target=account_checker, args=(emails, ))
    thread.start()

    manager = MailRuManager(accounts=emails)

    for email in emails:
        response = email.get_activation_url(waiting_time=0.1)
        if response["status"] == "error":
            email.activate()
            with open("email.txt", 'a') as f:
                f.write(f'{email.email}:{email.password}\n')
                f.close()
    stop = True


if __name__ == '__main__':
    stop = False
    main()
