from os import path
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

    def raw_data(self):
        return f'{self.email.email} - {self.username} - {self.password}'
