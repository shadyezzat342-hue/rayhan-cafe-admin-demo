"""Rayhan Cafe admin demo: REST API + static UI. Python stdlib only (sqlite3, http.server)."""
import json, os, random, re, sqlite3, sys, threading
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "demo.db"))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
STATUSES = ["new", "preparing", "ready", "delivered", "cancelled"]
lock = threading.Lock()

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

db = None

def init():
    global db
    fresh = not os.path.exists(DB)
    db = conn()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL, area TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, price REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), status TEXT NOT NULL, total REAL NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE, product_id INTEGER NOT NULL REFERENCES products(id), qty INTEGER NOT NULL, price REAL NOT NULL);
    """)
    if fresh: seed()

def seed():
    r = random.Random(7)
    prods = [("إسبريسو","مشروبات ساخنة",45),("كابتشينو","مشروبات ساخنة",60),("لاتيه","مشروبات ساخنة",65),("قهوة تركي","مشروبات ساخنة",40),
             ("آيس لاتيه","مشروبات باردة",70),("موهيتو","مشروبات باردة",55),("كرواسون","مخبوزات",50),("كيك شوكولاتة","حلويات",85),
             ("تشيز كيك","حلويات",95),("ساندوتش جبنة","وجبات",75)]
    db.executemany("INSERT INTO products(name,category,price) VALUES(?,?,?)", prods)
    names = ["أحمد علي","منى حسن","محمود سمير","سارة إبراهيم","يوسف خالد","نورا عادل","كريم مصطفى","هبة فاروق","عمر طارق","دينا ياسر","إسلام رضا","ليلى أمين"]
    areas = ["مدينة نصر","المعادي","الزمالك","التجمع","الدقي","مصر الجديدة"]
    now = datetime(2026, 11, 23, 18, 0)
    for i, n in enumerate(names):
        db.execute("INSERT INTO customers(name,phone,area,created_at) VALUES(?,?,?,?)",
                   (n, "0100%07d" % r.randint(1000000, 9999999), r.choice(areas), (now - timedelta(days=r.randint(30, 200))).isoformat()))
    for _ in range(140):
        t = now - timedelta(days=r.randint(0, 29), hours=r.randint(0, 9), minutes=r.randint(0, 59))
        items = [(r.randint(1, 10), r.randint(1, 3)) for _ in range(r.randint(1, 4))]
        total = sum(prods[p-1][2] * q for p, q in items)
        st = "delivered" if (now - t).days >= 1 and r.random() > .06 else r.choice(STATUSES)
        cur = db.execute("INSERT INTO orders(customer_id,status,total,created_at) VALUES(?,?,?,?)", (r.randint(1, len(names)), st, total, t.isoformat()))
        for p, q in items:
            db.execute("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)", (cur.lastrowid, p, q, prods[p-1][2]))
    db.commit()

def rows(sql, args=()):
    return [dict(x) for x in db.execute(sql, args).fetchall()]

def order_full(oid):
    o = rows("SELECT o.*, c.name customer_name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.id=?", (oid,))
    if not o: return None
    o = o[0]
    o["items"] = rows("SELECT oi.product_id, p.name, oi.qty, oi.price FROM order_items oi JOIN products p ON p.id=oi.product_id WHERE order_id=?", (oid,))
    return o

class Err(Exception):
    def __init__(s, code, msg): s.code, s.msg = code, msg

def route(method, path, q, body):
    p = [x for x in path.split("/") if x][1:]  # drop 'api'
    if p == ["products"] and method == "GET":
        return 200, rows("SELECT * FROM products ORDER BY id")
    if p == ["orders"] and method == "GET":
        sql, a = "SELECT o.*, c.name customer_name FROM orders o JOIN customers c ON c.id=o.customer_id WHERE 1=1", []
        if q.get("status"):
            if q["status"][0] not in STATUSES: raise Err(400, "حالة غير صحيحة")
            sql += " AND o.status=?"; a.append(q["status"][0])
        if q.get("q"):
            sql += " AND (c.name LIKE ? OR CAST(o.id AS TEXT)=?)"; a += ["%" + q["q"][0] + "%", q["q"][0]]
        return 200, rows(sql + " ORDER BY o.created_at DESC LIMIT 200", a)
    if p == ["orders"] and method == "POST":
        cid, items = body.get("customer_id"), body.get("items")
        if not rows("SELECT 1 FROM customers WHERE id=?", (cid,)): raise Err(400, "العميل غير موجود")
        if not isinstance(items, list) or not items: raise Err(400, "الطلب فاضي")
        total, clean = 0, []
        for it in items:
            pr = rows("SELECT * FROM products WHERE id=?", (it.get("product_id"),))
            qty = it.get("qty")
            if not pr or not isinstance(qty, int) or qty < 1 or qty > 50: raise Err(400, "منتج أو كمية غير صحيحة")
            clean.append((pr[0]["id"], qty, pr[0]["price"])); total += qty * pr[0]["price"]
        cur = db.execute("INSERT INTO orders(customer_id,status,total,created_at) VALUES(?,?,?,?)", (cid, "new", total, datetime.now().isoformat(timespec="seconds")))
        db.executemany("INSERT INTO order_items(order_id,product_id,qty,price) VALUES(?,?,?,?)", [(cur.lastrowid, *c) for c in clean])
        db.commit()
        return 201, order_full(cur.lastrowid)
    if len(p) == 2 and p[0] == "orders" and p[1].isdigit():
        oid = int(p[1]); o = order_full(oid)
        if not o: raise Err(404, "الطلب غير موجود")
        if method == "GET": return 200, o
        if method == "PATCH":
            if body.get("status") not in STATUSES: raise Err(400, "حالة غير صحيحة")
            db.execute("UPDATE orders SET status=? WHERE id=?", (body["status"], oid)); db.commit()
            return 200, order_full(oid)
        if method == "DELETE":
            db.execute("DELETE FROM orders WHERE id=?", (oid,)); db.commit(); return 200, {"deleted": oid}
    if p == ["customers"] and method == "GET":
        return 200, rows("SELECT c.*, COUNT(o.id) orders_count, COALESCE(SUM(CASE WHEN o.status!='cancelled' THEN o.total END),0) spent FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY spent DESC")
    if p == ["customers"] and method == "POST":
        name, phone = (body.get("name") or "").strip(), (body.get("phone") or "").strip()
        if not name or not re.fullmatch(r"01\d{9}", phone): raise Err(400, "الاسم مطلوب والموبايل لازم 11 رقم يبدأ بـ 01")
        cur = db.execute("INSERT INTO customers(name,phone,area,created_at) VALUES(?,?,?,?)", (name, phone, (body.get("area") or "").strip(), datetime.now().isoformat(timespec="seconds")))
        db.commit()
        return 201, rows("SELECT * FROM customers WHERE id=?", (cur.lastrowid,))[0]
    if p == ["reports", "summary"]:
        return 200, rows("""SELECT COUNT(*) orders, COALESCE(SUM(total),0) revenue, COALESCE(AVG(total),0) avg_order,
            (SELECT COUNT(*) FROM customers) customers, SUM(status IN('new','preparing')) open_orders
            FROM orders WHERE status!='cancelled'""")[0]
    if p == ["reports", "daily"]:
        return 200, rows("SELECT substr(created_at,1,10) day, COUNT(*) orders, SUM(total) revenue FROM orders WHERE status!='cancelled' GROUP BY day ORDER BY day DESC LIMIT 14")[::-1]
    if p == ["reports", "top-products"]:
        return 200, rows("SELECT p.name, SUM(oi.qty) qty, SUM(oi.qty*oi.price) revenue FROM order_items oi JOIN products p ON p.id=oi.product_id JOIN orders o ON o.id=oi.order_id WHERE o.status!='cancelled' GROUP BY p.id ORDER BY revenue DESC LIMIT 5")
    if p == ["reports", "by-status"]:
        return 200, rows("SELECT status, COUNT(*) n FROM orders GROUP BY status")
    raise Err(404, "المسار غير موجود")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, data, ctype="application/json; charset=utf-8"):
        b = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def handle_any(self, method):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = {}
                if n:
                    try: body = json.loads(self.rfile.read(n))
                    except ValueError: raise Err(400, "JSON غير صالح")
                    if not isinstance(body, dict): raise Err(400, "JSON غير صالح")
                with lock: code, data = route(method, u.path, parse_qs(u.query), body)
                self.send(code, data)
            except Err as e: self.send(e.code, {"error": e.msg})
            except Exception as e: self.send(500, {"error": "خطأ في السيرفر"}); print("ERR", e, file=sys.stderr)
            return
        if method != "GET": return self.send(405, {"error": "method not allowed"})
        f = "index.html" if u.path == "/" else u.path.lstrip("/")
        full = os.path.abspath(os.path.join(STATIC, f))
        if not full.startswith(STATIC + os.sep) or not os.path.isfile(full): return self.send(404, b"not found", "text/plain")
        ct = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css"}.get(os.path.splitext(full)[1], "application/octet-stream")
        self.send(200, open(full, "rb").read(), ct)
    do_GET = lambda s: s.handle_any("GET")
    do_POST = lambda s: s.handle_any("POST")
    do_PATCH = lambda s: s.handle_any("PATCH")
    do_DELETE = lambda s: s.handle_any("DELETE")

if __name__ == "__main__":
    init()
    port = int(os.environ.get("PORT", 8000))
    print(f"Rayhan admin demo on http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
