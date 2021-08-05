from multiprocessing.dummy import Pool


class RegistrationManager:
    def __init__(self, db, accounts=[]):
        self.accounts = accounts
        self.db = db

    def add_account(self, account):
        self.accounts.append(account)

    def register(self, i):
        pass

    def start_registration(self, threads=2):

        pool = Pool(threads)
        pool.map(self.register, [x for x in range(len(self.accounts))])


class FunPayManager(RegistrationManager):
    def register(self, i):
        account = self.accounts[i]

        last_step = account.register()

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
        pass
