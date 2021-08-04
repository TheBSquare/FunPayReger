from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from seleniumwire.undetected_chromedriver.v2 import Chrome, ChromeOptions
from twocaptcha import TwoCaptcha
import email as email_parser
from os import path
import imaplib
import time

from secret import api_token
from settings import profiles_path, driver_path
from multiprocessing.dummy import Pool


class Proxy:
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.is_auth = not self.username is None and not self.password is None
        self.http = f"http://{self.ip}:{self.port}" if not self.is_auth else f"http://{self.username}:{self.password}@{self.ip}:{self.port}"
        self.https = f"https://{self.ip}:{self.port}" if not self.is_auth else f"https://{self.username}:{self.password}@{self.ip}:{self.port}"


class Email:
    def __init__(self, email, domain, password):
        self.email = email
        self.domain = domain
        self.password = password

        self.raw = f'{"-" * 20}\n{self.email = }\n{self.domain = }\n{self.password = }\n'

    def get_activation_url(self, waiting_time, filter_="(UNSEEN)"):

        upper_bound = time.time() + waiting_time

        while time.time() < upper_bound:
            email = imaplib.IMAP4_SSL(f'imap.{self.domain}')
            email.login(self.email, self.password)
            email.select("inbox")

            result, data = email.uid('search', None, filter_)
            ids = data[0].split()

            if len(ids) == 0:
                continue

            for id_ in ids:
                message = email_parser.message_from_bytes(email.uid('fetch', id_, "(RFC822)")[1][0][1])

                if "FunPay" not in str(message["From"]):
                    continue

                text = message.get_payload(decode=True).decode().split('\n')

                for part in text:
                    if '/account/activate?token=' in part:
                        return str(part)


class Account:
    def __init__(self, email, username, password, proxy=None):
        self.email = email
        self.username = username
        self.password = password
        self.proxy = proxy

        self.profile_path = path.join(profiles_path, f'Profile_{self.email.email}')
        self.raw = f"{self.email.raw}{self.username = }\n{self.password = }\n{'-' * 20}"

        self.options = ChromeOptions()
        self.options.headless = True
        self.options.user_data_dir = self.profile_path

        self.proxy_options = {
            'disable_capture': True,
            'verify_ssl': False,
        }

        if not self.proxy is None:
            self.proxy_options["proxy"] = {
                'http': self.proxy.http,
                'https': self.proxy.https,
                'no_proxy': 'localhost,127.0.0.1'
            }

        self.url = "https://funpay.ru/en/account/register"
        self.driver = None
        self.steps = {"working": {"status": False}}

    def register(self):

        self.steps["working"] = {"status": True}

        # step: driver

        try:
            self.steps["driver"] = {"status": "loading"}
            self.driver = Chrome(
                executable_path=driver_path,
                options=self.options,
                seleniumwire_options=self.proxy_options
            )
            wait = WebDriverWait(self.driver, 60, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
            self.steps["driver"] = {"status": "ok"}
        except Exception as err:
            self.steps["driver"] = {"status": "error", "description": str(err)}
            self.steps["working"] = {"status": False}
            return False

        # step: page

        try:
            self.steps["page"] = {"status": "loading"}
            self.driver.get(self.url)
            wait_0 = WebDriverWait(self.driver, 600, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
            wait_0.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.g-recaptcha")))
            self.steps["page"] = {"status": "ok"}
        except Exception as err:
            self.steps["page"] = {"status": "error", "description": str(err)}
            self.steps["working"] = {"status": False}
            return False

        # step: input_data

        key = None
        try:
            self.steps["input_data"] = {"status": "loading"}
            data = {
                "name": self.username,
                "email": self.email.email,
                "password": self.password
            }
            for key in data:
                element = wait.until(EC.element_to_be_clickable((By.NAME, key)))

                for char in data[key]:
                    element.send_keys(char)

                time.sleep(.3)

            key = "checkbox"
            self.driver.find_element(By.CSS_SELECTOR, "div.checkbox > label > i").click()

            self.steps["input_data"] = {"status": "ok"}
        except Exception as err:
            self.steps["input_data"] = {"status": "error", "description": f'{key = }, {err = }'}
            self.steps["working"] = {"status": False}
            return False

        # step: captcha

        try:
            self.steps["captcha"] = {"status": "loading"}

            site_key = self.driver.find_element(By.CSS_SELECTOR, "div.g-recaptcha").get_attribute("data-sitekey")

            solver = TwoCaptcha(api_token, pollingInterval=15)
            solution_data = solver.recaptcha(sitekey=site_key, url=self.url)

            self.driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{solution_data["code"]}"')

            self.steps["captcha"] = {"status": "ok"}
        except Exception as err:
            self.steps["captcha"] = {"status": "error", "description": str(err)}
            self.steps["working"] = {"status": False}
            return False

        # step: submitting

        try:
            self.steps["submitting"] = {"status": "loading"}
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-primary.btn-block"))).click()
            self.steps["submitting"] = {"status": "ok"}
        except Exception as err:
            self.steps["submitting"] = {"status": "error", "description": str(err)}
            self.steps["working"] = {"status": False}
            return False

        # step: check

        try:
            self.steps["check"] = {"status": "loading"}
            wait_ = WebDriverWait(self.driver, 7, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
            err = wait_.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.form-messages.text-danger"))).text
            self.steps["check"] = {"status": "error", "description": err}
            self.steps["working"] = {"status": False}
            return err
        except TimeoutException:
            self.steps["check"] = {"status": "ok"}

        # step: validating

        try:
            self.steps["validating"] = {"status": "loading"}
            validation_url = self.email.get_activation_url(15)

            if validation_url is None:
                validation_url = self.email.get_activation_url(waiting_time=0.1, filter_="ALL")

            self.driver.get(validation_url)
            time.sleep(10)
            self.steps["validating"] = {"status": "ok"}
            self.steps["working"] = {"status": False}
        except Exception as err:
            self.steps["validating"] = {"status": "error", "description": str(err)}
            self.steps["working"] = {"status": False}
            return False

        return True


class RegistrationManager:
    def __init__(self, db, accounts=[]):
        self.accounts = accounts
        self.db = db

    def add_account(self, account):
        self.accounts.append(account)

    def start_registration(self, threads=2):
        def register(i):
            token = self.db.create_connection()
            response = accounts[i].register()
            accounts[i].driver.close()
            accounts[i].driver.quit()
            if response:
                self.db.update_account(accounts[i], status=3, token=token)
            elif "This email account is already in use" in response:
                self.db.update_account(accounts[i], status=1, token=token)
            self.db.commit_connection(token)
            self.db.close_connection(token)

        accounts = self.accounts

        pool = Pool(threads)
        pool.map(register, [x for x in range(len(self.accounts))])
