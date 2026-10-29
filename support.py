"""Where users send feedback: a GitHub Issues page. Pure Python so it is testable anywhere."""
import platform
import urllib.parse

import config as C

# ---- SET THIS to your repo's issues page, e.g. "https://github.com/yourname/detent/issues" ----
ISSUES_URL = "https://github.com/SurbD/detent/issues"
# ------------------------------------------------------------------------------------------------


def is_configured(url=None):
    url = url or ISSUES_URL
    return url.startswith("https://github.com/") and "YOUR-NAME" not in url


def new_issue_url(kind="feedback", url=None, version=None, system=None):
    """Link to a new GitHub issue, pre-filled with the version info people always forget to give.
    kind = "feedback" or "bug" (bug = they just made a report zip and should attach it)."""
    url = (url or ISSUES_URL).rstrip("/")
    version = version or C.VERSION
    system = system or platform.platform()
    if kind == "bug":
        title = "Bug: "
        body = ("**What happened?**\n\n\n**What did you expect?**\n\n\n"
                "**Report zip:** drag the detent-report-….zip file into this box.\n\n")
    else:
        title = ""
        body = "**Your feedback or idea:**\n\n\n"
    body += f"---\nDetent {version} · {system}"
    return f"{url}/new?" + urllib.parse.urlencode({"title": title, "body": body})
