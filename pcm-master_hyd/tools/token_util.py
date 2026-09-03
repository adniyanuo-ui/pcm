# _*_coding:utf-8_*_
# __author: guo
import os
import time

import jwt
import datetime


class Token:
    secret = {
        "web": os.getenv("PCM_WEB_JWT_SECRET", "development-web-secret"),
        "cms": os.getenv("PCM_CMS_JWT_SECRET", "development-cms-secret"),
        "mobile": os.getenv("PCM_MOBILE_JWT_SECRET", "development-mobile-secret"),
    }

    @classmethod
    def encode(cls, payload, timeout=None, key="web"):
        if isinstance(timeout, datetime.timedelta):
            payload["exp"] = datetime.datetime.now(datetime.UTC) + timeout
        result = jwt.encode(payload, cls.secret[key], algorithm="HS256")
        return result

    @classmethod
    def decode(cls, s, key="web"):
        payload = jwt.decode(s, cls.secret[key], algorithms=["HS256"])
        return payload


token = Token

if __name__ == '__main__':
    print(time.time())
    auth = token.encode({"username": "test", "uid": 10}, datetime.timedelta(seconds=3))
    print(len(auth), auth)
    data = token.decode(auth)
    print((time.time() - data["exp"]) / 60 / 60)
