class Address:
    def __init__(self, url, expiration_time, headers, body):
        self.url = url
        self.expiration_time = expiration_time
        self.headers = headers
        self.body = body
