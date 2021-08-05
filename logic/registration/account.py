from os import path

import requests
from bs4 import BeautifulSoup
from twocaptcha import TwoCaptcha

from logic.registration.utils import step
from settings import profiles_path


class Account:
    def __init__(self, email, username, password, proxy=None):
        self.email = email
        self.username = username
        self.password = password
        self.proxy = proxy

        self.profile_path = path.join(profiles_path, f'Profile_{self.email.email}')

        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q = 0.9",
            "referer": "https://funpay.ru/en/",
            "sec-ch-ua": '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        }

        if self.proxy is None:
            self.proxies = {}
        else:
            self.proxies = {"https": self.proxy.http}

        self.steps = {"working": {"status": "waiting"}}

    @step
    def preparing(self):
        data = self.email.get_activation_url(0.1, "(UNSEEN)")

        if data is None:
            data = self.email.get_activation_url(0.1, "(SEEN)")
            if data is None:
                return {"need_activation": False}
            else:
                raise Exception("Account has already been activated")
        elif data["status"] == "error":
            raise Exception(data)
        else:
            return {"need_activation": True}

    @step
    def activating(self):
        activation = self.email.get_activation_url(5)
        requests.get(activation["url"], headers=self.headers, proxies=self.proxies)
        return {"data": activation}

    @step
    def pre_reg(self):
        session = requests.Session()
        url = "https://funpay.ru/en/account/register"
        response = session.get(url, headers=self.headers, proxies=self.proxies)

        if response.status_code != 200:
            raise ConnectionError(f"Cannot connect to funpay, {response.status_code = }")

        self.headers["referer"] = url

        data = {
            "name": self.username,
            "email": self.email.email,
            "password": self.password,
            "agreement": "on"
        }

        soup = BeautifulSoup(response.content, "html.parser")
        data["csrf_token"] = eval(soup.select_one('body')["data-app-data"])["csrf-token"]
        site_key = soup.select_one("div.g-recaptcha")["data-sitekey"]
        return {"site_key": site_key, "data": data, "session": session}

    @step
    def captcha(self, site_key):
        url = "https://funpay.ru/en/account/register"
        solver = TwoCaptcha('219dbbd99e9eec8e9e5973c5f9389607', pollingInterval=10)
        solution_data = solver.recaptcha(sitekey=site_key, url=url)
        return {"captcha_solution": solution_data["code"]}

    @step
    def reg(self, session, data):
        url = "https://funpay.ru/en/account/register"
        response = session.post(url, headers=self.headers, data=data)

        if response.status_code != 200:
            raise ConnectionError(f"Cannot connect to funpay, {response.status_code = }")

        soup = BeautifulSoup(response.content, "html.parser")
        warning = soup.select_one("ul.form-messages.text-danger")

        if not warning is None:
            raise Exception(warning.text)

        return {"session": session}

    def register(self):

        self.steps["working"] = {"status": "ok"}

        # step: preparing
        step_result = self.preparing(step_name="preparing")

        if step_result["status"] == "error":
            return step_result

        elif step_result["need_activation"]:
            step_result = self.activating(step_name="activating")

            if step_result["status"] == "ok":
                self.steps["working"]["status"] = "finished"

            return step_result

        # step: pre_reg
        step_result = self.pre_reg(step_name="pre_reg")
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
        step_result = self.reg(step_name="reg", session=session, data=data)
        if step_result["status"] == "error":
            return step_result

        # step: activating
        step_result = self.activating(step_name="activating")
        if step_result["status"] == "ok":
            self.steps["working"]["status"] = "finished"
        return step_result
