"""python tests/test_support.py  - feedback link + installer autostart hand-off (no Windows needed)."""
import os, sys, tempfile, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
import support as S

REPO = "https://github.com/someone/detent/issues"

def test_placeholder_is_not_configured():
    assert not S.is_configured(S.ISSUES_URL) or "YOUR-NAME" not in S.ISSUES_URL
    assert not S.is_configured("https://github.com/YOUR-NAME/detent/issues")
    assert not S.is_configured("http://example.com/x")
    assert S.is_configured(REPO)

def test_new_issue_link_prefilled():
    u = S.new_issue_url("feedback", url=REPO + "/", version="9.9", system="Windows-11")
    assert u.startswith(REPO + "/new?")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query, keep_blank_values=True)
    assert "Detent 9.9" in q["body"][0] and "Windows-11" in q["body"][0]
    b = S.new_issue_url("bug", url=REPO, version="9.9", system="W")
    qb = urllib.parse.parse_qs(urllib.parse.urlparse(b).query)
    assert qb["title"][0].startswith("Bug") and ".zip" in qb["body"][0]

def test_installer_choice_overrides_and_saves():
    p = os.path.join(tempfile.mkdtemp(), "c.json")
    c = C.Config(); C.save(c, p)
    C.apply_installer_choice(c, False, p)
    assert c.autostart is False and C.load(p).autostart is False     # unticked in installer -> off and remembered
    C.apply_installer_choice(c, None, p)
    assert C.load(p).autostart is False                              # no new installer choice -> unchanged
    C.apply_installer_choice(c, True, p)
    assert C.load(p).autostart is True

def test_pop_installer_autostart_is_noop_off_windows():
    if sys.platform != "win32":
        assert C.pop_installer_autostart() is None

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
