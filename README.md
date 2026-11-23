# Rayhan Cafe Admin (demo)

Arabic (RTL) admin dashboard with a real backend: Python 3 standard library + SQLite. No packages to install.
**Demo only:** all names, phones, orders and prices are generated fake data. There is no login, so do not expose it publicly with real data.

## Run
    python3 server.py        # http://localhost:8000  (PORT=9000 to change)
The database `demo.db` is created and seeded on first start (12 customers, 10 products, 140 orders). Delete it to reset.

## REST API (JSON)
| Method | Path | Notes |
|---|---|---|
| GET | /api/orders?status=&q= | list, filter by status or customer/order id |
| POST | /api/orders | `{customer_id, items:[{product_id, qty}]}`, total computed on the server |
| GET/PATCH/DELETE | /api/orders/{id} | PATCH `{status}` |
| GET/POST | /api/customers | POST validates name and 11-digit 01xxxxxxxxx phone |
| GET | /api/products | |
| GET | /api/reports/summary, daily, top-products, by-status | aggregates in SQL |

Invalid input returns 400 with an Arabic `error` message; unknown ids return 404.

## UI
Dashboard (KPIs, daily revenue chart, top products), orders (filter, search, create, change status), customers (add, spend totals), reports.

## Hosting a live demo
Any host that runs a Python process (Render, Railway, Fly.io): start command `python3 server.py`, it reads `PORT`. SQLite lives on local disk, so use a persistent disk or accept resets on redeploy. Add authentication before using real data.
