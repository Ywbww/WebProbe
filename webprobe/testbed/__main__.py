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

import secrets

from flask import Flask, jsonify, make_response, redirect, request, session
from flask.sessions import SessionInterface, SessionMixin

app = Flask(__name__)
app.secret_key = "webprobe-testbed-not-for-production"


# --- Custom SessionInterface (Gap 5 (i) lock) ---------------------------
# Single SessionInterface implementation closes 3 module fixtures:
#   1. session.session_fixation        — sid stable across login transition
#   2. headers.cookie_no_httponly      — cookie set without HttpOnly
#   3. auth.detect_shared_session      — PHPSESSID is in the frozenset
# Replicated verbatim per Item 8b spec block.

_TESTBED_SESSIONS: dict[str, dict] = {}


class FixationVulnerableSession(dict, SessionMixin):
    def __init__(self, sid: str, initial: dict = None):
        super().__init__(initial or {})
        self.sid = sid
        self.modified = False


class FixationVulnerableSessionInterface(SessionInterface):
    """Deliberately broken: does NOT regenerate session ID on login.
    Real-world equivalent: server-side session store where the developer
    forgets to rotate the session ID across an auth state transition."""

    def open_session(self, app, request):
        sid = request.cookies.get("PHPSESSID")
        if sid is None or sid not in _TESTBED_SESSIONS:
            sid = secrets.token_urlsafe(16)
            _TESTBED_SESSIONS[sid] = {}
        return FixationVulnerableSession(sid, _TESTBED_SESSIONS[sid])

    def save_session(self, app, session, response):
        if session.modified:
            _TESTBED_SESSIONS[session.sid] = dict(session)
        # Always set cookie to current sid — does NOT rotate on login (deliberate flaw).
        response.set_cookie("PHPSESSID", session.sid, httponly=False)


app.session_interface = FixationVulnerableSessionInterface()


# --- Login state (per-source-IP for /login-locked) ----------------------
KNOWN_USERS: set[str] = {"admin", "alice", "bob"}
_LOCKED_ATTEMPTS: dict[str, int] = {}


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


# --- GET/POST /login : user-enum diff + no-lockout target ---------------
_LOGIN_FORM_HTML = """<!DOCTYPE html>
<html><head><title>Login</title></head>
<body>
<h1>Sign in</h1>
<form method="POST" action="/login">
  <input type="text" name="user" placeholder="username">
  <input type="password" name="password" placeholder="password">
  <button type="submit">Sign in</button>
</form>
</body></html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return _LOGIN_FORM_HTML
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    if not user or not password:
        return "Missing credentials", 401
    if user not in KNOWN_USERS:
        # Gap 2: distinct body for unknown user enables user-enum diff.
        return "Unknown user", 401
    if user == "admin":
        session["role"] = "admin"
    else:
        session["role"] = "user"
    session.modified = True
    return redirect("/", code=302)


# --- GET/POST /login-locked : per-source-IP lockout target --------------
@app.route("/login-locked", methods=["GET", "POST"])
def login_locked():
    if request.method == "GET":
        # Login form so setup_form_login (Phase 5b) can do its initial GET
        # discovery before the brute_force module begins POSTing wrong
        # passwords. Body shape mirrors /login.
        return _LOGIN_FORM_HTML.replace('action="/login"', 'action="/login-locked"')
    src = request.remote_addr or "unknown"
    attempts = _LOCKED_ATTEMPTS.get(src, 0) + 1
    _LOCKED_ATTEMPTS[src] = attempts
    if attempts > 5:
        return "Account temporarily locked due to too many failed attempts.", 429
    return "Invalid credentials", 401


# --- POST /logout : Gap 4 — session not cleared -------------------------
@app.route("/logout", methods=["POST"])
def logout():
    # Deliberately do NOT call session.clear() — cookie remains valid for
    # subsequent authed requests (session.session_persists_post_logout
    # acceptance target).
    return jsonify({"status": "logged out"})


# --- POST /csrf-broken : csrf_missing target ----------------------------
@app.route("/csrf-broken", methods=["POST"])
def csrf_broken():
    # No CSRF-token validation. Accepts any POST.
    return jsonify({"status": "ok"})


# --- GET /admin/ : access_control role_violation target -----------------
@app.route("/admin/")
def admin_panel():
    if session.get("role") == "admin":
        body = (
            "<html><head><title>Admin Dashboard</title></head><body>"
            "<h1>Admin Dashboard</h1>"
            "<h2>All Users</h2>"
            "<ul><li>admin</li><li>alice</li><li>bob</li></ul>"
            "</body></html>"
        )
        return body, 200
    return "Forbidden", 403


# --- GET /idor/<id> : cross_account_leak target -------------------------
@app.route("/idor/<int:id>")
def idor(id):
    """Same body for ANY authenticated session — cross-session sha256 match
    enables idor cross_account_leak."""
    return jsonify({"id": id, "data": f"resource-{id}-data"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9999, debug=False)
