from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to access API

DB_PATH = "factures.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                title TEXT,
                amount REAL,
                date TEXT,
                items TEXT,
                photo_url TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        ''')

@app.before_request
def setup():
    init_db()

# --- CUSTOMERS ---
@app.route('/api/customers', methods=['GET'])
def get_customers():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM customers").fetchall()
        customers = [dict(row) for row in rows]
    return jsonify(customers)

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO customers (name) VALUES (?)", (name,))
        conn.commit()
        customer_id = cur.lastrowid
    return jsonify({"id": customer_id, "name": name}), 201

@app.route('/api/customers/<int:cid>', methods=['DELETE'])
def delete_customer(cid):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM invoices WHERE customer_id = ?", (cid,))
        cur.execute("DELETE FROM customers WHERE id = ?", (cid,))
        if cur.rowcount == 0:
            return jsonify({"error": "Customer not found"}), 404
        conn.commit()
    return '', 204

# --- INVOICES ---
@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    customer_id = request.args.get('customer_id')
    query = "SELECT * FROM invoices WHERE customer_id = ?" if customer_id else "SELECT * FROM invoices"
    params = (customer_id,) if customer_id else ()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        invoices = [dict(row) for row in rows]
    return jsonify(invoices)

@app.route('/api/invoices', methods=['POST'])
def add_invoice():
    data = request.json
    required = ['customer_id', 'title', 'date']
    if not all(data.get(f) is not None for f in required):
        return jsonify({"error": "Missing required fields"}), 400
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO invoices (customer_id, title, amount, date, items, photo_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['customer_id'],
            data.get('title'),
            data.get('amount', 0),
            data.get('date'),
            json.dumps(data.get('items', [])),
            data.get('photo_url')
        ))
        conn.commit()
        invoice_id = cur.lastrowid
    return jsonify({"id": invoice_id, **data}), 201

@app.route('/api/invoices/<int:inv_id>', methods=['DELETE'])
def delete_invoice(inv_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM invoices WHERE id = ?", (inv_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Invoice not found"}), 404
        conn.commit()
    return '', 204

# Health check
@app.route('/')
def home():
    return "Factures API is running!"

if __name__ == '__main__':

    app.run(port=int(os.environ.get("PORT", 5000)))
