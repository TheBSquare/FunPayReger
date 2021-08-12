import os
from logic.registration import Proxy

root_path = os.getcwd()

profiles_path = os.path.join(root_path, 'resources', 'profiles')

error_pictures_path = os.path.join(root_path, 'resources', 'errors')

driver_path = os.path.join(root_path, "resources", "drivers", "chromedriver")

database_path = os.path.join(root_path, "resources", "funpay.db")

email_logs = os.path.join(root_path, "resources", "logs", "email_logs.txt")

funpay_logs = os.path.join(root_path, "resources", "logs", "funpay_logs.txt")

captcha_path = os.path.join(root_path, "resources", "captcha")

sms_activate_token = "22683779bA3f095Af217721b056dfe84"
two_captcha_token = "219dbbd99e9eec8e9e5973c5f9389607"

proxy = Proxy(
    ip="p.webshare.io",
    port="80",
    username="xemhxukj-rotate",
    password="3ddt7kiqtlca"
)
