import sqlite3
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "todo.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"  # needed for flash messages


# ---------- Database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---------- Routes ----------
@app.route("/")
def index():
    filter_by = request.args.get("filter", "all")
    query = "SELECT * FROM tasks"
    if filter_by == "active":
        query += " WHERE completed = 0"
    elif filter_by == "completed":
        query += " WHERE completed = 1"
    query += " ORDER BY completed ASC, id DESC"

    tasks = get_db().execute(query).fetchall()
    counts = get_db().execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(completed), 0) AS done FROM tasks"
    ).fetchone()
    return render_template("index.html", tasks=tasks, counts=counts, filter_by=filter_by)


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Task cannot be empty.", "warning")
    else:
        db = get_db()
        db.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        db.commit()
        flash("Task added.", "success")
    return redirect(url_for("index"))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        flash("Task not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Task cannot be empty.", "warning")
            return render_template("edit.html", task=task)
        db.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
        db.commit()
        flash("Task updated.", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", task=task)


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle_task(task_id):
    db = get_db()
    db.execute(
        "UPDATE tasks SET completed = 1 - completed WHERE id = ?", (task_id,)
    )
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    flash("Task deleted.", "info")
    return redirect(request.referrer or url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
