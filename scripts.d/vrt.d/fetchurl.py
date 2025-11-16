# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
import requests

class FetchDesc(object):
    def __init__(self, url):
        self.url_       = url
        self.body_      = None
        self.http_code_ = None

    def fetch(self):
        try:
            response = requests.get(self.url_)
        except requests.RequestException as e:
            self.body_      = None  # None --> Nothing fetched.
            self.http_code_ = None  # None --> Network error.
            return

        try:
            self.body_ = response.text
        except Exception:
            self.body_ = response.content.decode(errors="replace")
        finally:
            self.http_code_ = response.status_code
