class Proxy:
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.is_auth = not self.username is None and not self.password is None
        self.http = f"http://{self.ip}:{self.port}" if not self.is_auth else f"http://{self.username}:{self.password}@{self.ip}:{self.port}"
        self.https = f"https://{self.ip}:{self.port}" if not self.is_auth else f"https://{self.username}:{self.password}@{self.ip}:{self.port}"


