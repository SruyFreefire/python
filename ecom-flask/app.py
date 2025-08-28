import os
import json
import sqlite3
from datetime import datetime
from functools import wraps
from urllib import request as urlrequest, parse as urlparse, error as urlerror

from flask import (
    Flask, render_template, g, redirect, url_for, request, flash, session, abort
)
from flask_mail import Mail, Message

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "store.db")

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'your_mail_server'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your_username'
app.config['MAIL_PASSWORD'] = 'your_password'
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@example.com'

mail = Mail(app)

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production"

# ---- Category & rating shown in UI (DB stays exactly: id, title, description, price, image)
CATEGORY_MAP = {
    1: "Headphones",
    2: "Smartwatch",
    3: "Camera",
    4: "Sneakers",
    5: "Backpack",
    6: "Sunglasses",
    7: "Laptop",
    8: "Phone",
    9: "Coffee",
    10: "Chair",
}
RATING_MAP = {
    1: 4.7, 2: 4.4, 3: 4.8, 4: 4.2, 5: 4.6,
    6: 4.1, 7: 4.9, 8: 4.5, 9: 4.3, 10: 4.0
}


# -------------------- DB helpers --------------------
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL
        )
    """)
    db.commit()

def seed_db_if_empty():
    db = get_db()
    cur = db.execute("SELECT COUNT(*) as c FROM products")
    count = cur.fetchone()["c"]
    if count > 0:
        return

    # 10 real image URLs (picsum stable IDs)
    seed = [
        dict(title="Wireless Headphones",
             description="Over-ear Bluetooth with ANC and long battery life.",
             price=99.99, image="https://picsum.photos/id/1062/800/800"),
        dict(title="Smartwatch Pro",
             description="Fitness tracking, heart rate, GPS, and notifications.",
             price=149.00, image="https://picsum.photos/id/903/800/800"),
        dict(title="Mirrorless Camera",
             description="24MP APS-C sensor with 4K video and fast autofocus.",
             price=649.00, image="https://picsum.photos/id/250/800/800"),
        dict(title="Running Sneakers",
             description="Lightweight, breathable mesh with responsive cushioning.",
             price=79.50, image="https://picsum.photos/id/21/800/800"),
        dict(title="Urban Backpack",
             description="Water-resistant rolltop fits 15\" laptop and accessories.",
             price=59.99, image="https://picsum.photos/id/1084/800/800"),
        dict(title="Polarized Sunglasses",
             description="UV400 protection with classic frame and sturdy hinges.",
             price=39.99, image="https://picsum.photos/id/582/800/800"),
        dict(title="Ultrabook 14\"",
             description="8GB RAM, 512GB SSD, backlit keyboard, all-day battery.",
             price=899.00, image="https://picsum.photos/id/7/800/800"),
        dict(title="5G Smartphone",
             description="6.5\" OLED display, 128GB storage, excellent cameras.",
             price=499.00, image="https://picsum.photos/id/1011/800/800"),
        dict(title="Single-Origin Coffee",
             description="Freshly roasted beans, 1 lb bag, notes of chocolate.",
             price=16.50, image="https://picsum.photos/id/35/800/800"),
        dict(title="Ergonomic Chair",
             description="Lumbar support, adjustable arms, breathable mesh.",
             price=219.00, image="https://picsum.photos/id/433/800/800"),
    ]
    for p in seed:
        db.execute(
            "INSERT INTO products (title, description, price, image) VALUES (?, ?, ?, ?)",
            (p["title"], p["description"], p["price"], p["image"])
        )
    db.commit()

def get_product(pid):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    return row

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Please log in as admin.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


# -------------------- Public pages --------------------
@app.route("/")
def home():
    init_db()
    seed_db_if_empty()
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("home.html",
                           products=products,
                           category_map=CATEGORY_MAP,
                           rating_map=RATING_MAP)

@app.route("/product/<int:pid>")
def product_detail(pid):
    p = get_product(pid)
    if not p:
        abort(404)
    return render_template("product_detail.html",
                           p=p,
                           category=CATEGORY_MAP.get(pid, "General"),
                           rating=RATING_MAP.get(pid, 4.5))

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    products = []
    if q:
        like = f"%{q}%"
        db = get_db()
        products = db.execute(
            "SELECT * FROM products WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC",
            (like, like)
        ).fetchall()
    return render_template("search.html", q=q, products=products,
                           category_map=CATEGORY_MAP, rating_map=RATING_MAP)

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "GET":
        return render_template("order.html")
    # POST - finalize order
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    phone = request.form.get("phone", "").strip()
    note = request.form.get("note", "").strip()
    order_json = request.form.get("order_json", "{}")
    try:
        data = json.loads(order_json)
    except Exception:
        data = {}
    items = data.get("items", [])
    total = data.get("total", 0)

    # Build Telegram message
    lines = []
    lines.append("🛒 *New Order*")
    if name:
        lines.append(f"*Name:* {name}")
    if phone:
        lines.append(f"*Phone:* {phone}")
    if note:
        lines.append(f"*Note:* {note}")
    lines.append("")
    if items:
        lines.append("*Items:*")
        for it in items:
            title = it.get("title", "Item")
            qty = it.get("qty", 1)
            price = it.get("price", 0)
            subtotal = float(qty) * float(price)
            lines.append(f"• {title} × {qty} = ${subtotal:,.2f}")
    lines.append("")
    lines.append(f"*Total:* ${float(total):,.2f}")
    message_text = "\n".join(lines)

    bot_token ="8015114450:AAHlpryTRdyyC7jD2LqJXBUVAQ5Zp8S5Rl8"
    chat_id = "@mengsruy"
    if bot_token and chat_id:
        try:
            endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "Markdown"
            }
            data = urlparse.urlencode(payload).encode()
            req = urlrequest.Request(endpoint, data=data)
            urlrequest.urlopen(req, timeout=10)  # fire and forget
        except urlerror.URLError:
            # silently ignore; order still completes
            pass
    # Redirect to a page that clears localStorage then goes home
    return redirect(url_for("order_complete"))

@app.route("/order/complete")
def order_complete():
    return render_template("order_complete.html")


# -------------------- Admin --------------------
@app.route("/admin", methods=["GET"])
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_do_login():
    user = request.form.get("username", "")
    pw = request.form.get("password", "")
    if user == "admin" and pw == "123":
        session["admin"] = True
        flash("Welcome, admin!", "success")
        return redirect(url_for("admin_dashboard"))
    flash("Invalid credentials.", "danger")
    return redirect(url_for("admin_login"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    db = get_db()
    total_products = db.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    # Fake dashboard KPIs
    kpis = {
        "visitors_today": 1248,
        "conversion_rate": 3.7,
        "revenue_today": 1894.50,
        "pending_orders": 5
    }
    # small chart data
    chart_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    chart_data = [12, 19, 9, 14, 22, 17, 25]
    return render_template("admin_dashboard.html",
                           total_products=total_products,
                           kpis=kpis,
                           chart_labels=chart_labels,
                           chart_data=chart_data)

@app.route("/admin/products")
@admin_required
def admin_products():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("admin_products_list.html", products=products)

@app.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
def admin_product_new():
    if request.method == "GET":
        return render_template("admin_product_form.html", mode="new", p=None)
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    price = float(request.form.get("price","0") or 0)
    image = request.form.get("image","").strip()
    if not (title and description and image):
        flash("Please fill all required fields.", "warning")
        return redirect(url_for("admin_product_new"))
    db = get_db()
    db.execute("INSERT INTO products (title, description, price, image) VALUES (?,?,?,?)",
               (title, description, price, image))
    db.commit()
    flash("Product created.", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/<int:pid>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(pid):
    db = get_db()
    p = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not p:
        abort(404)
    if request.method == "GET":
        return render_template("admin_product_form.html", mode="edit", p=p)
    title = request.form.get("title","").strip()
    description = request.form.get("description","").strip()
    price = float(request.form.get("price","0") or 0)
    image = request.form.get("image","").strip()
    if not (title and description and image):
        flash("Please fill all required fields.", "warning")
        return redirect(url_for("admin_product_edit", pid=pid))
    db.execute("UPDATE products SET title=?, description=?, price=?, image=? WHERE id=?",
               (title, description, price, image, pid))
    db.commit()
    flash("Product updated.", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/<int:pid>/delete", methods=["GET", "POST"])
@admin_required
def admin_product_delete(pid):
    db = get_db()
    p = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not p:
        abort(404)
    if request.method == "GET":
        return render_template("admin_confirm_delete.html", p=p)
    db.execute("DELETE FROM products WHERE id = ?", (pid,))
    db.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))
@app.context_processor
def inject_year():
    return {"current_year": datetime.utcnow().year}


if __name__ == "__main__":
    # Ensure DB initialized/seeds on first run
    with app.app_context():
        init_db()
        seed_db_if_empty()
    app.run(debug=True)
