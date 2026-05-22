"""A deliberately-vulnerable login form for the SQL Injection 101 challenge.
DO NOT use this code as a template for anything real."""

import os
import sqlite3
from flask import Flask, request, render_template_string

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "ctf{placeholder}")

LOGIN_HTML = """
<!doctype html>
<title>Login</title>
<h1>Internal Admin Portal</h1>
<form method="POST">
  <input name="username" placeholder="Username"/>
  <input name="password" placeholder="Password" type="password"/>
  <button type="submit">Login</button>
</form>
{% if message %}<p>{{ message }}</p>{% endif %}
"""


def init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE users (username TEXT, password TEXT)")
    conn.execute("INSERT INTO users VALUES ('admin', 'super-secret-never-guessed')")
    conn.execute("INSERT INTO users VALUES ('guest', 'guest123')")
    return conn


db = init_db()


@app.route("/", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        # ⚠️ INTENTIONALLY VULNERABLE — DO NOT COPY ⚠️
        query = f"SELECT username FROM users WHERE username = '{u}' AND password = '{p}'"
        try:
            row = db.execute(query).fetchone()
            if row and row[0] == "admin":
                message = f"Welcome, admin. Your flag: {FLAG}"
            elif row:
                message = f"Welcome, {row[0]}. (You need to login as 'admin' for the flag.)"
            else:
                message = "Invalid credentials."
        except sqlite3.Error as e:
            message = f"Database error: {e}"
    return render_template_string(LOGIN_HTML, message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)))
