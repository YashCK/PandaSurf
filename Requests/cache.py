import time

from Requests.address import Address


class Cache:
    def __init__(self):
        self.storage = {}

    @staticmethod
    def is_address_expired(address: Address) -> bool:
        return address.expiration_time > time.time()

    def get_address(self, url) -> Address | None:
        if url in self.storage:
            return self.storage[url]
        return None

    def add_address(self, address: Address):
        self.storage[address.url] = address

    def delete_address(self, url):
        del self.storage[url]

    def __str__(self):
        stored_urls = "{"
        for url in self.storage:
            stored_urls += url + "\n"
        stored_urls = stored_urls[:-1]
        stored_urls += "}"
        return stored_urls
