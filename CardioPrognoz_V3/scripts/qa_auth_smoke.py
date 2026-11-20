"""Black-box HTTP smoke: login, refreshed CSRF token, integration action.

Runs only against a disposable local educational environment, with a
synthetic account. A missing mock is expected in the load-test container.
"""

import http.cookiejar
import os
import re
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("LZ11_BASE_URL", "http://127.0.0.1:8000")
USERNAME = os.environ.get("LZ11_QA_USERNAME", "synthetic_qa")
PASSWORD = os.environ.get("LZ11_QA_PASSWORD")
TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def request_page(opener, path, data=None):
    request = urllib.request.Request(BASE_URL + path, data=data)
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def extract_token(html):
    found = TOKEN_RE.search(html)
    if not found:
        raise RuntimeError("No CSRF token was rendered")
    return found.group(1)


def main():
    if not PASSWORD:
        raise RuntimeError("LZ11_QA_PASSWORD is required")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    status, login_html = request_page(opener, "/login")
    if status != 200:
        raise RuntimeError(f"Login page returned {status}")
    payload = urllib.parse.urlencode({
        "username": USERNAME, "password": PASSWORD,
        "csrf_token": extract_token(login_html),
    }).encode("utf-8")
    status, home_html = request_page(opener, "/login", payload)
    if status != 200 or "Ввод медицинских показателей" not in home_html:
        raise RuntimeError("Synthetic user could not log in")
    status, integration_html = request_page(opener, "/integration")
    if status != 200:
        raise RuntimeError("Integration page unavailable after login")
    action = urllib.parse.urlencode({
        "record_id": "SYN-001", "csrf_token": extract_token(integration_html),
    }).encode("utf-8")
    status, response_html = request_page(opener, "/integration/mock", action)
    if status == 400 and "mock-сервис недоступен" in response_html:
        print("Smoke OK: login + renewed CSRF + offline mock handled explicitly")
        return
    if status == 200 and "SYN-001" in response_html:
        print("Smoke OK: login + renewed CSRF + synthetic mock record")
        return
    raise RuntimeError(f"Unexpected integration response {status}: CSRF or routing may be broken")


if __name__ == "__main__":
    main()
