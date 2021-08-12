import datetime
import glob
import os
import random

from selenium.webdriver.support.select import Select
from twocaptcha import TwoCaptcha
from undetected_chromedriver.v2 import Chrome, ChromeOptions
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException, TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from settings import driver_path, profiles_path, captcha_path
from logic.utils.utils import step
from logic.services import SmsActivate
from datetime import datetime
import email as email_parser
import imaplib
import time
import shutil


class Email:
    def __init__(self, email, domain, password, spare_mail=None):
        self.spare_mail = spare_mail
        self.email = email
        self.domain = domain
        self.password = password
        self.temp_password = self.password
        self.token = self.password
        self.sub_domain = self.email.split("@")[1]

        self.steps = {"working": {"status": "waiting"}}

    def raw_data(self):
        return f"{self.email = } - {self.password = } - {self.temp_password = } - {self.token = }"

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
        options.add_argument("--window-size=760,1080")
        options.page_load_strategy = 'eager'
        options.add_argument("--proxy-server=http://p.webshare.io:9999")

        self.driver = Chrome(
            executable_path=driver_path,
            options=options
        )

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
        self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="enter-password"]').click()
        wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="login-to-mail"]').click()

        try:
            wait0 = WebDriverWait(self.driver, 15, poll_frequency=.5, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
            element = wait0.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[data-test-id="error-footer-text"]')))
            raise Exception(str(element.text))
        except TimeoutException:
            pass

        return {"wait": wait}

    @step
    def activate_imap(self, wait):
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, f'div[aria-label="{self.email}"]'))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[href="https://id.mail.ru/security"]'))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[data-test-id="app-passwords-item"]'))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[data-name="add-button"]'))).click()

        wait.until(EC.visibility_of_element_located((By.NAME, "name"))).send_keys("IMAP")
        self.driver.find_element(By.CSS_SELECTOR, 'button[data-name="submit"]').click()
        wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, 'button[data-name="submit"]').click()
        password = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.view_dialog__password"))).text
        self.token = password
        self.driver.find_element(By.CSS_SELECTOR, '#PH_user-email').click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[href="https://id.mail.ru/security"]'))).click()
        return {"password": password}

    @step
    def change_password(self, password, wait):
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.base-0-2-82.base-d5-0-2-111.fluid-0-2-86"))).click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input.input-0-2-160.withIcon-0-2-161"))).send_keys(self.password)
        self.driver.find_element(By.NAME, "new-password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "form > div:nth-child(14) > div:nth-child(2) > div > div > input").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button.base-0-2-82.base-d7-0-2-181.primary-0-2-93.auto-0-2-107").click()
        self.password = password
        return {}

    @step
    def pre_reg(self):
        self.driver.get("https://account.mail.ru/signup?from=main&rf=auth.mail.ru")
        wait = WebDriverWait(self.driver, .5, poll_frequency=.5, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
        triggers = (((By.NAME, "fname"), "default"), ((By.CSS_SELECTOR, "div.vkc__Button__title"), "connect"))
        t1 = time.time() + 600
        while t1 > time.time():
            for trigger in triggers:
                try:
                    wait.until(EC.visibility_of_element_located(trigger[0]))
                    return {"way": trigger[1]}
                except TimeoutException:
                    pass
        raise Exception("Cant define registration type")

    @step
    def confirm_phone(self):
        wait = WebDriverWait(self.driver, 80, poll_frequency=.7, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a[data-test-id="resend-callui-link"]'))).click()
        
        sms_activate = SmsActivate()

        code = sms_activate.wait_for_sms(wait_time=300, frequency=7)

        self.driver.find_element(By.CSS_SELECTOR, 'input[data-test-id="code"]').send_keys(str(code))
        self.driver.find_element(By.CSS_SELECTOR, 'button[data-test-id="verification-next-button"]').click()
        self.driver.find_element(By.CSS_SELECTOR, 'form > button[data-test-id="first-step-submit"]').click()

    @step
    def reg_default(self):
        email, domain = self.email.split("@")
        first_name, last_name, birthday = email.split(".")
        birthday = datetime.strptime(birthday, "%m%d%Y")
        sex = random.choice(["male", "female"])

        wait = WebDriverWait(self.driver, 60, poll_frequency=1, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])

        wait.until(EC.visibility_of_element_located((By.NAME, "fname"))).send_keys(first_name)
        last_name, self.driver.find_element(By.NAME, "lname").send_keys(last_name)

        Select(self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-id="birth-date__day"] > select')).select_by_value(birthday.strftime("%d"))
        Select(self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-id="birth-date__month"] > select')).select_by_value(birthday.strftime("%m"))
        Select(self.driver.find_element(By.CSS_SELECTOR, 'div[data-test-id="birth-date__year"] > select')).select_by_value(birthday.strftime("%Y"))

        self.driver.find_element(By.CSS_SELECTOR, f'label[data-test-id="gender-{sex}"]').click()

        self.driver.find_element(By.NAME, "username").send_keys(email)
        self.driver.find_element(By.NAME, "password").send_keys(self.password)
        self.driver.find_element(By.NAME, "repeatPassword").send_keys(self.password)

        try:
            self.driver.find_element(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(self.spare_mail)
            return {"way": "spare_mail"}
        except NoSuchElementException:
            pass

        try:
            self.driver.find_element(By.CSS_SELECTOR, 'a[data-test-id="phone-number-switch-link"]').click()
            wait._timeout = 5
            wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(self.spare_mail)
            return {"way": "spare_mail"}
        except NoSuchElementException:
            pass

        sms_activate = SmsActivate()

        self.driver.find_element(By.CSS_SELECTOR, 'input[data-test-id="phone-input"]').send_keys(sms_activate.number[1:])
        self.driver.find_element(By.CSS_SELECTOR, 'form > button[data-test-id="first-step-submit"]').click()
        return {"way": "phone"}

    @step
    def captcha(self, wait):
        file_name = os.path.join(captcha_path, f"{datetime.now().strftime('%m%d%Y%H%M%S')}.png")

        try:
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'img[data-test-id="captcha-image"]'))).click()
            self.driver.switch_to.window(self.driver.window_handles[-1])
        except TimeoutException:
            return {"description": "no captcha detected"}

        solver = TwoCaptcha('219dbbd99e9eec8e9e5973c5f9389607')
        solution = solver.normal(file_name)["code"]

        self.step_input(solution, self.driver.find_element(By.CSS_SELECTOR, 'input[data-test-id="captcha"]'))
        self.driver.find_element(By.CSS_SELECTOR, 'form > button[data-test-id="verification-next-button"]').click()
        return {}

    @step
    def text_captcha(self, wait):
        file_name = os.path.join(captcha_path, f"{datetime.now().strftime('%m%d%Y%H%M%S')}.png")

        try:
            element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'img.js-captcha-img.b-captcha__captcha')))
            element.screenshot_as_png(file_name)
        except TimeoutException:
            return {"description": "no captcha detected"}
        input("asdasd: ")
        solver = TwoCaptcha('219dbbd99e9eec8e9e5973c5f9389607')
        solution = solver.normal(file_name)["code"]

        self.driver.find_element(By.CSS_SELECTOR, 'input[data-test-id="captcha"]').send_keys(solution)
        self.driver.find_element(By.CSS_SELECTOR, 'form > button[data-test-id="verification-next-button"]').click()
        return {}

    def step_input(self, value, element):
        for char in value:
            element.send_keys(char)

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

        # step: captcha
        step_result = self.text_captcha(
            step_name="captcha",
            wait=WebDriverWait(self.driver, 10, poll_frequency=.5, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
        )
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result

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

    def register(self):
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

        # step: pre_reg
        step_result = self.pre_reg(step_name="pre_reg")
        if step_result["status"] == "error":
            additional0 = self.close_driver(step_name="close_driver")
            additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
            step_result.update({"additional0": additional0})
            step_result.update({"additional1": additional1})
            return step_result

        print(f'{step_result["way"]}: ')

        if step_result["way"] == "default":

            # step: reg
            step_result = self.reg_default(step_name="reg")
            if step_result["status"] == "error":
                additional0 = self.close_driver(step_name="close_driver")
                additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
                step_result.update({"additional0": additional0})
                step_result.update({"additional1": additional1})
                return step_result
            wait = step_result["wait"]

            if step_result["way"] == "spare_mail":
                # step: confirmation
                step_result = self.text_captcha(step_name="confirmation")
                if step_result["status"] == "error":
                    additional0 = self.close_driver(step_name="close_driver")
                    additional1 = self.remove_profile(step_name="remove_profile", profile_path=profile_path)
                    step_result.update({"additional0": additional0})
                    step_result.update({"additional1": additional1})
                    return step_result

            elif step_result["way"] == "phone":
                pass

        elif step_result["way"] == "connect":
            time.sleep(5)

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
