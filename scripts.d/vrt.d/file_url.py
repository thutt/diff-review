# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import urllib

import file_access

class URLFileAccess(file_access.FileAccess):
    def __init__(self, root_url, ack_insecure_cert):
        super().__init__(root_url)
        if not root_url.endswith("/"):
            # Requirement of urllib.parse.urljoin()
            root_url = "%s/" % (root_url)
        self.root_url_          = root_url
        self.ack_insecure_cert_ = ack_insecure_cert

    def read_(self, pathname):
        import fetchurl

        url  = urllib.parse.urljoin(self.root_url_, pathname)
        desc = fetchurl.FetchDesc(url, self.ack_insecure_cert_)
        desc.fetch()

        if desc.http_code_ is None:
            result = [
                "An unidentified network error occurred during the download of",
                "",
                "  %s" % (url),
                "",
                "No HTTP code was produced, so this is most likely to be",
                "a network infrastructure error, or the web server is down.",
                "",
                "The file contents could not be retrieved."
            ]
            return '\n'.join(result)
        else:
            if desc.http_code_ == 200:
                return desc.body_
            else:
                result = [
                    "Fetching the following URL",
                    "",
                    "  %s" % (url),
                    "",
                    "produced this HTML response code: %s" % (desc.http_code_),
                    "",
                    "The file contents could not be retrieved."
                ]
                return '\n'.join(result)
