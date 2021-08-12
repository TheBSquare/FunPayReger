from logic.binaries import funpay, mailru


def main():
    operation = {
        '1': funpay.start,
        '2': mailru.start,
    }[
        input(
            f'1. Reg FunPay\n'
            f'2. Reg MailRu\n'
            f'Operation: '
        )
    ]()


def test():
    import requests
    from logic.registration import Account, Email

    email = Email(email="minka.denis@gmail.com", password="22SAS61796SAS", domain="gmail.com")

    account = Account(username="pizda", password="bforsandsforb1005", email=email)
    print(account.raw_data())

    url = "https://funpay.ru/en/account/login"


if __name__ == '__main__':
    test()
