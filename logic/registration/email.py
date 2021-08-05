import glob
import os

from undetected_chromedriver.v2 import Chrome, ChromeOptions
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from settings import driver_path, profiles_path
from logic.registration.utils import step
import email as email_parser
import imaplib
import time
import shutil


class Email:
    def __init__(self, email, domain, password):
        self.email = email
        self.domain = domain
        self.password = password
        self.sub_domain = email.split("@")[1]

        self.steps = {"working": {"status": "waiting"}}

    def get_activation_url(self, waiting_time, filter_="(UNSEEN)"):

        upper_bound = time.time() + waiting_time

        try:
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
                        if '/account/activate?token=' not in part:
                            continue

                        return {"status": "ok", "url": str(part)}

        except Exception as err:
            return {"status": "error", "description": str(err)}

    @step
    def profile_path(self):
        i = 0

        for profile in glob.glob(f'{profiles_path}/*'):
            profile_i = int(profile.split('\\')[-1])
            if i != profile_i:
                break
            else:
                i += 1

        return {"profile_path": os.path.join(profiles_path, str(i))}

    @step
    def init_driver(self, profile_path):
        options = ChromeOptions()
        options.headless = False
        options.user_data_dir = profile_path

        self.driver = Chrome(
            executable_path=driver_path,
            options=options
        )
        self.driver.maximize_window()
        return {"driver": self.driver}

    @step
    def close_driver(self):
        self.driver.quit()
        return {}

    @step
    def remove_profile(self, profile_path):
        t = time.time() + 10
        while time.time() < t:
            try:
                shutil.rmtree(profile_path)
                return {}
            except PermissionError:
                pass

        raise Exception("Cant delete or find profile path")

    @step
    def authorization(self):
        self.driver.get("https://mail.ru/")
        wait = WebDriverWait(self.driver, 60, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])

        wait.until(EC.visibility_of_element_located((By.NAME, "login"))).send_keys(self.email)
        self.driver.find_element(By.CSS_SELECTOR, "button.button.svelte-1eyrl7y").click()
        wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, "button.second-button.svelte-1eyrl7y").click()

        try:
            wait0 = WebDriverWait(self.driver, 5, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
            element = wait0.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.error.svelte-1eyrl7y")))
            raise Exception(str(element.text))
        except TimeoutException:
            pass

        return {"wait": wait}

    @step
    def activate_imap(self, wait):
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ph-project.ph-project__account.svelte-a0l97g"))).click()
        self.driver.find_element(By.CSS_SELECTOR, "div.ph-sidebar.svelte-app5g7 > div > div > a:nth-child(3)").click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.Layout-mobile__container--2MbDy > div > a:nth-child(14)"))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.btn.btn_stylish.btn_responsive.btn_main"))).click()

        wait.until(EC.visibility_of_element_located((By.NAME, "name"))).send_keys("IMAP")
        self.driver.find_element(By.CSS_SELECTOR, "button.btn.btn_main.btn_stylish.btn_responsive").click()
        wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, "button.btn.btn_main.btn_stylish.btn_responsive").click()
        password = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.view_dialog__password"))).text
        return {"password": password}

    @step
    def change_password(self, password, wait):
        self.driver.get("https://id.mail.ru/security")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.base-0-2-82.base-d5-0-2-111.fluid-0-2-86"))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input.input-0-2-160.withIcon-0-2-161"))).send_keys(self.password)
        self.driver.find_element(By.NAME, "new-password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "form > div:nth-child(14) > div:nth-child(2) > div > div > input").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button.base-0-2-82.base-d7-0-2-181.primary-0-2-93.auto-0-2-107").click()
        self.password = password
        return {}

    def activate(self):
        self.steps["working"] = {"status": "ok"}

        # step: profile_path
        step_result = self.profile_path(step_name="profile_path")
        if step_result["status"] == "error":
            return step_result

        profile_path = step_result["profile_path"]

        # step: init_driver
        step_result = self.init_driver(step_name="init_driver", profile_path=profile_path)
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result

        # step: authorization
        step_result = self.authorization(step_name="authorization")
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result
        wait = step_result["wait"]

        # step: activating_imap
        step_result = self.activate_imap(step_name="activate_imap", wait=wait)
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result

        password = step_result["password"]

        # step: change_password
        step_result = self.change_password(step_name="activate_imap", password=password, wait=wait)
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result

        # step: close_driver
        step_result = self.close_driver(step_name="close_driver")
        if step_result["status"] == "error":
            additional0 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            return step_result

        # step: remove_profile
        step_result = self.remove_profile(step_name="remove_profile", profile_path=profile_path)

        if step_result["status"] == "ok":
            self.steps["working"]["status"] = "finished"

        return step_result
