"""WebProbe testbed — Flask harness for v2 detection-module acceptance.

PRD ref: prd.md > Epic 5 > Story 5.4. Spec ref: spec.md > Testbed.

Stateless endpoints (Item 8a) and stateful endpoints (Item 8b) live in
the same module. Stateful endpoints rely on a deliberately-broken custom
SessionInterface (`FixationVulnerableSessionInterface`) that does NOT
rotate the session ID across login transitions — required by the session
fixation acceptance fixture (Phase 1 Q1 Gap 5 (i) lock).

Run with: `python3 -m webprobe.testbed` (binds 127.0.0.1:9999).
"""
from __future__ import annotations

from flask import Flask, jsonify, make_response, redirect, request

app = Flask(__name__)
app.secret_key = "webprobe-testbed-not-for-production"


# --- Story 5.4 detection endpoint ---------------------------------------
@app.route("/__webprobe_testbed__/health")
def health():
    return jsonify({"webprobe_testbed": True, "testbed_version": "2.0.0"})


# --- GET / : root with deliberate flaws ---------------------------------
_ROOT_HTML = """<!DOCTYPE html>
<html><head><title>WebProbe Testbed</title></head>
<body>
<h1>WebProbe Testbed</h1>
<p>Deliberately-broken target for module acceptance.</p>

<form method="POST" action="/csrf-broken">
  <input type="hidden" name="_csrfToken" value="abc123">
  <input type="text" name="comment">
  <button type="submit">Submit (CSRF-broken)</button>
</form>

<form method="GET" action="">
  <input type="text" name="q">
  <button type="submit">Search (CakePHP empty-action edge case)</button>
</form>

<p>Try the dynamic seed: <a href="?id=1">item 1</a></p>
</body></html>
"""


@app.route("/")
def root():
    """Root page — deliberately omits CSP, HSTS, X-Frame-Options.
    Cookie set without Secure / HttpOnly / SameSite (headers-audit feed).
    Body carries 2 forms (CSRF-broken + empty-action) + ?id= dynamic seed.
    """
    resp = make_response(_ROOT_HTML)
    # Note: even though the stateful endpoints (Item 8b) will set a real
    # PHPSESSID via the custom SessionInterface, we still emit a flawed
    # PHPSESSID here on the unauth root so the headers cookie audit fires
    # without any prior authenticated request.
    resp.headers["Set-Cookie"] = "PHPSESSID=anonymous-testbed-cookie; Path=/"
    return resp


# --- GET /server-info : info-disclosure target --------------------------
@app.route("/server-info")
def server_info():
    body = (
        "# DB password: testbed-leak-do-not-use\n"
        "Server: nginx/1.18, internal IP 10.0.0.5\n"
        "uptime: 4 days\n"
    )
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


# --- GET /.htaccess : sensitive_path_exposed_high -----------------------
@app.route("/.htaccess")
def htaccess():
    body = (
        "Options -Indexes\n"
        "RewriteEngine On\n"
        "RewriteRule ^admin/(.*)$ /admin.php?$1 [L]\n"
        "AuthType Basic\n"
        "AuthName \"Restricted Area\"\n"
        "AuthUserFile /var/www/.htpasswd\n"
        "Require valid-user\n"
    )
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


# --- GET /cpanel : sensitive_path_exposed_medium ------------------------
@app.route("/cpanel")
def cpanel():
    body = (
        "<html><head><title>cPanel Login</title></head>"
        "<body><h1>cPanel</h1>"
        "<form method='POST' action='/cpanel/login'>"
        "<input name='user'><input name='pass' type='password'>"
        "<button>Sign in</button></form></body></html>"
    )
    return body, 200


# --- GET /reflect-xss?q=... : reflected XSS target ----------------------
@app.route("/reflect-xss")
def reflect_xss():
    q = request.args.get("q", "")
    return f"<html><body>You searched: {q}</body></html>"


# --- GET /vulnerable?q=... : SQLi error-string target -------------------
@app.route("/vulnerable")
def vulnerable():
    q = request.args.get("q", "")
    if "'" in q or '"' in q:
        body = (
            f"<html><body><h1>Database error</h1>"
            f"<pre>Error: You have an error in your SQL syntax near '{q}' "
            f"at line 1</pre></body></html>"
        )
        return body, 200
    return f"<html><body>Result for {q}</body></html>", 200


# --- GET /search?q=... : stack-trace leakage on quote injection ---------
@app.route("/search")
def search():
    q = request.args.get("q", "")
    if "'" in q or '"' in q:
        trace = (
            "Traceback (most recent call last):\n"
            "  File \"/app/views/search.py\", line 42, in search\n"
            "    cursor.execute(f\"SELECT * FROM items WHERE name = '{q}'\")\n"
            "  File \"/usr/lib/python3.11/sqlite3/dbapi2.py\", line 117, in execute\n"
            "    return self._impl.execute(sql)\n"
            "sqlite3.OperationalError: near \"'\": syntax error\n"
        )
        return trace, 500, {"Content-Type": "text/plain; charset=utf-8"}
    return f"<html><body>Search results for: {q}</body></html>", 200


# --- GET /file?name=... : path traversal target -------------------------
@app.route("/file")
def file_serve():
    name = request.args.get("name", "")
    if ".." in name:
        passwd = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
            "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
        )
        return passwd, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return f"<html><body>file: {name}</body></html>", 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9999, debug=False)
