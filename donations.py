import sqlite3
from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

DB = "food_donation.db"  
# ------------------------------
# ROUTE: Show receiver dashboard
# ------------------------------
@app.route("/receiver")
def receiver_dashboard():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all available food listings
    cur.execute("SELECT * FROM food_listing WHERE status='available'")
    listings = cur.fetchall()
    conn.close()

    return render_template("receiver.html", listings=listings)

# ------------------------------
# ROUTE: Assign / Take a listing
# ------------------------------
@app.route("/take/<int:listing_id>")
def take_listing(listing_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Update listing status to 'assigned'
    cur.execute("DELETE FROM food_listing WHERE id=?", (listing_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("receiver_dashboard"))

# ------------------------------
# RUN SERVER
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)