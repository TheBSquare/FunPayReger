from datetime import datetime
from multiprocessing.dummy import Pool

import requests
from bs4 import BeautifulSoup
from twocaptcha import TwoCaptcha

from logic.utils import run_as_thread
from logic.utils.utils import step
from settings import two_captcha_token


class RegistrationManager:
    def __init__(self, db, accounts=[]):
        self.accounts = accounts
        self.db = db
        self.stop = False

    def add_account(self, account):
        self.accounts.append(account)

    def register(self, i):
        pass

    def start_registration(self, threads=2):
        pool = Pool(threads)
        pool.map(self.register, [x for x in range(len(self.accounts))])

    @run_as_thread
    def start_logger(self, accounts, output):
        temp = {}
        total = len(accounts)
        print(f'Total: {total}')
        while not self.stop:
            for account in accounts:
                if account.username in temp:
                    for step_key in account.steps.copy():
                        if step_key not in temp[account.username] or account.steps[step_key]["status"] != temp[account.username][step_key]["status"]:
                            temp[account.username][step_key] = account.steps[step_key]
                            s = f'{temp[account.username]["number"]}.{datetime.now().strftime("%m/%d/%Y-%H:%M.%S")} - ' \
                                f'{account.raw_data()}'
                            with open(output, 'a') as f:
                                f.write(f'{s}\n')
                                f.close()
                            print(s)

                    if account.steps["working"]["status"] == "error" or account.steps["working"]["status"] == "finished":
                        del temp[account.username]

                else:
                    if account.steps["working"]["status"] == "waiting":
                        pass
                    elif account.steps["working"]["status"] == 'ok' and account.username not in temp:
                        temp[account.username] = {"number": total}
                        total -= 1


class FunPayRegistrationManager(RegistrationManager):
    @step
    def preparing(self, account):
        data = account.email.get_activation_url(0.1, "(UNSEEN)")

        if data is None:
            data = account.email.get_activation_url(0.1, "(SEEN)")
            if data is None:
                return {"need_activation": False}
            else:
                raise Exception("Account has already been activated")
        elif data["status"] == "error":
            raise Exception(data)
        else:
            return {"need_activation": True}

    @step
    def activating(self, account):
        activation = account.email.get_activation_url(5)
        requests.get(activation["url"], headers=account.headers, proxies=account.proxies)
        return {"data": activation}

    @step
    def pre_reg(self, account):
        session = requests.Session()
        url = "https://funpay.ru/en/account/register"
        response = session.get(url, headers=account.headers, proxies=account.proxies)

        if response.status_code != 200:
            raise ConnectionError(f"Cannot connect to funpay, {response.status_code = }")

        account.headers["referer"] = url

        data = {
            "name": account.username,
            "email": account.email.email,
            "password": account.password,
            "agreement": "on"
        }

        soup = BeautifulSoup(response.content, "html.parser")
        data["csrf_token"] = eval(soup.select_one('body')["data-app-data"])["csrf-token"]
        site_key = soup.select_one("div.g-recaptcha")["data-sitekey"]
        return {"site_key": site_key, "data": data, "session": session}

    @step
    def captcha(self, site_key):
        url = "https://funpay.ru/en/account/register"
        solver = TwoCaptcha(two_captcha_token, pollingInterval=10)
        solution_data = solver.recaptcha(sitekey=site_key, url=url)
        return {"captcha_solution": solution_data["code"]}

    @step
    def reg(self, session, data, account):
        url = "https://funpay.ru/en/account/register"
        response = session.post(url, headers=account.headers, data=data)

        if response.status_code != 200:
            raise ConnectionError(f"Cannot connect to funpay, {response.status_code = }")

        soup = BeautifulSoup(response.content, "html.parser")
        warning = soup.select_one("ul.form-messages.text-danger")

        if not warning is None:
            raise Exception(warning.text)

        return {"session": session}

    def register_account(self, account):
        account.steps["working"] = {"status": "ok"}

        # step: preparing
        step_result = self.preparing(step_name="preparing", account=account)

        if step_result["status"] == "error":
            return step_result

        elif step_result["need_activation"]:
            step_result = self.activating(step_name="activating")

            if step_result["status"] == "ok":
                account.steps["working"]["status"] = "finished"

            return step_result

        # step: pre_reg
        step_result = self.pre_reg(step_name="pre_reg", account=account)
        if step_result["status"] == "error":
            return step_result

        site_key = step_result["site_key"]
        session = step_result["session"]
        data = step_result["data"]

        # step: captcha
        step_result = self.captcha(step_name="captcha", site_key=site_key)
        if step_result["status"] == "error":
            return step_result

        data["g-recaptcha-response"] = step_result["captcha_solution"]

        # step: reg
        step_result = self.reg(step_name="reg", session=session, data=data, account=account)
        if step_result["status"] == "error":
            return step_result

        # step: activating
        step_result = self.activating(step_name="activating", account=account)
        if step_result["status"] == "ok":
            account.steps["working"]["status"] = "finished"
        return step_result

    def register(self, i):
        account = self.accounts[i]

        last_step = self.register_account(account)

        token = self.db.create_connection()
        if account.steps["working"]["status"] == "finished":
            self.db.update_account(account, status=1, token=token)
        elif last_step["status"] == "error":
            if "This email account is already in use" in last_step["description"]:
                self.db.update_account(account, status=2, token=token)
            elif "Account has already been activated" in last_step["description"]:
                self.db.update_account(account, status=3, token=token)

        self.db.commit_connection(token)
        self.db.close_connection(token)


class MailRuManager(RegistrationManager):
    def register(self, i):
        account = self.accounts[i]
        account.register()


class MailRuActivationManager(RegistrationManager):
    def register(self, i):
        account = self.accounts[i]
        account.activate()
