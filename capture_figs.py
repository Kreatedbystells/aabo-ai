"""Recapture the interface figures over one fresh, deliberately ordered demo replay.

Run against the local server (127.0.0.1:8077) with a freshly reset database, so every figure
shows the same session's scan log, growing by one row per scan, with one timestamp. Each capture
below is the state a figure in Chapter Four asserts, in the order that makes the log coherent:

  001  www.gtbank.com/personal-banking            legitimate                    ss_legit_verdict
  002  aacworks.com/.../verify.php                phishing (hostile full URL)   ss_full_page
  003  www.jumia.com.ng/phones-tablets/           unverified - Nigerian list    ss_conflict_jumia
  004  nou.edu.ng/student-portal                  unverified - restricted reg.  ss_restricted_registry
  005  chairdoctorng.com/services                 unverified - operator list    (log row only)
  006  gtbank.com/personal-banking                legitimate (bare host)        ss_bare_host_fixed
  007  aldi.nivdostore.shop/verify/account        unverified - domain-first     ss_domain_first
  008  (empty field)                              landing state                 ss_landing

Row 008 is captured last, with the field cleared, so the landing figure shows the scan log the
replay has built up behind it. It is here because it is the figure whose wording goes stale most
easily: it shows the masthead, the badge row and the footer, so any change to those three must
re-run this script.

`ss_false_positive.png` is deliberately NOT captured here and must never be re-shot: it is the
record of what the first-generation model (rf-v1) displayed for a well-known legitimate login page,
taken from a build that is no longer deployed, and Chapter Four cites it as historical evidence
rather than as the current interface. Its caption says so.

Row 007 is a hostile shape whose *domain* reads as legitimate on its own, so the domain-first rule
fires. It is not on the bundled hostile blocklist, which is deliberate: a listed domain would take
the supporting-list branch instead and would not show the notice this figure documents.
"""
import base64
import json
import subprocess
import time

FIGS = "/Users/amarachi/Downloads/Stella_Project/artifacts/figs"
STATES = object()

PLAN = [
    ("https://www.gtbank.com/personal-banking", "ss_legit_verdict"),
    ("http://aacworks.com/wp-admin/images/system/template/verify.php", "ss_full_page"),
    ("https://www.jumia.com.ng/phones-tablets/", "ss_conflict_jumia"),
    ("https://nou.edu.ng/student-portal", "ss_restricted_registry"),
    ("https://chairdoctorng.com/services", None),
    ("https://google.com", "ss_bare_host_fixed"),
    ("https://www.boc.com/fr-fr/resources/secure-content-infographic", "ss_domain_first"),
]

new_tab("http://127.0.0.1:8077")
wait_for_load()
cdp("Emulation.setDeviceMetricsOverride", width=1180, height=900, deviceScaleFactor=1.5,
    mobile=False)
time.sleep(1)

for url, name in PLAN:
    js("""(() => {
      const i = document.querySelector('input#url');
      i.value = %s;
      i.dispatchEvent(new Event('input', {bubbles: true}));
      document.querySelector('button#go, button').click();
      return true;
    })()""" % json.dumps(url))
    time.sleep(3.5)
    state = js("""(() => {
      const g = s => (document.querySelector(s) || {}).textContent;
      const n = document.querySelector('#note');
      return {stamp: (g('#stamp') || '').trim(),
              note: n ? (n.className.includes('warn') ? 'WARN' : 'INFO') : 'none',
              shown: (g('#stamp') || '').trim()};
    })()""")
    rows = js("""(() => document.querySelectorAll('#log tr, .logn tr, [id*=log] tr').length)()""")
    print(f"{url[:58]:60s} -> {state['stamp']:11s} note={state['note']:5s} logrows~{rows}")
    if name:
        h = js("(() => Math.ceil(document.documentElement.scrollHeight))()")
        shot = cdp("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                   clip={"x": 0, "y": 0, "width": 1180, "height": h, "scale": 1})
        path = f"{FIGS}/{name}.png"
        open(path, "wb").write(base64.b64decode(shot["data"]))
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                             capture_output=True, text=True).stdout
        dims = " ".join(x.split(": ")[1] for x in out.strip().splitlines()[1:])
        print(f"      saved {name}.png  {dims}  (h_css={h})")
# Row 008: the landing state. Clear the field, let the normalisation hint disappear, and capture
# the whole page — masthead, badge row, specimens, the log the replay built, and the footer.
js("""(() => {
  const i = document.querySelector('input#url');
  i.value = '';
  i.dispatchEvent(new Event('input', {bubbles: true}));
  i.blur();
  return true;
})()""")
time.sleep(1.5)
h = js("(() => Math.ceil(document.documentElement.scrollHeight))()")
shot = cdp("Page.captureScreenshot", format="png", captureBeyondViewport=True,
           clip={"x": 0, "y": 0, "width": 1180, "height": h, "scale": 1})
path = f"{FIGS}/ss_landing.png"
open(path, "wb").write(base64.b64decode(shot["data"]))
out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                     capture_output=True, text=True).stdout
dims = " ".join(x.split(": ")[1] for x in out.strip().splitlines()[1:])
print(f"      saved ss_landing.png  {dims}  (h_css={h})")
print("done")
