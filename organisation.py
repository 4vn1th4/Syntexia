from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------- CREATE TABLES ----------
@app.route("/setup")
def setup():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT,
            quantity TEXT,
            location TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS organisations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_name TEXT,
            contact TEXT,
            city TEXT
        )
    """)

    conn.commit()
    conn.close()
    return "Database ready"


# ---------- ADD LISTING (PROVIDER) ----------
@app.route("/add_listing", methods=["POST"])
def add_listing():
    data = request.json

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO donations (food_name, quantity, location) VALUES (?, ?, ?)",
        (data["food_name"], data["quantity"], data["location"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Listing added successfully"})


# ---------- VIEW ORGANISATIONS (PROVIDER) ----------
@app.route("/get_organisations", methods=["GET"])
def get_organisations():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM organisations")
    rows = cur.fetchall()

    organisations = []
    for row in rows:
        organisations.append({
            "id": row["id"],
            "org_name": row["org_name"],
            "contact": row["contact"],
            "city": row["city"]
        })

    conn.close()
    return jsonify(organisations)


# ---------- VIEW DONATIONS (RECEIVER) ----------
@app.route("/get_donations", methods=["GET"])
def get_donations():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM donations")
    rows = cur.fetchall()

    donations = []
    for row in rows:
        donations.append({
            "id": row["id"],
            "food_name": row["food_name"],
            "quantity": row["quantity"],
            "location": row["location"]
        })

    conn.close()
    return jsonify(donations)


if __name__ == "__main__":
    app.run(debug=True)