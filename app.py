# backend/app.py - UPDATED WITH BETTER ERROR HANDLING
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'food_donation.db')


app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'food-donation-secret'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# ========== SIMPLIFIED DATABASE MODELS ==========
class FoodListing(db.Model):
    __tablename__ = 'food_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=1)
    expiry_date = db.Column(db.String(20))  # Store as string for simplicity
    location = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    
    # AI fields - make them nullable for now
    ai_status = db.Column(db.String(50), default='pending')
    ai_reason = db.Column(db.Text, default='')
    
    status = db.Column(db.String(20), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'food_name': self.food_name,
            'quantity': self.quantity,
            'expiry_date': self.expiry_date,
            'location': self.location,
            'lat': self.lat,
            'lng': self.lng,
            'ai_status': self.ai_status,
            'ai_reason': self.ai_reason,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    address = db.Column(db.String(300))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'lat': self.lat,
            'lng': self.lng,
            'phone': self.phone,
            'email': self.email
        }

# ========== SIMPLE AI CLASSIFIER ==========
class FoodSafetyAI:
    def classify(self, food_name, expiry_date):
        """Super simple AI - just checks expiry date"""
        try:
            today = datetime.now().date()
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            days_left = (expiry - today).days
            
            if days_left < 0:
                return {'status': 'reject', 'reason': 'Expired food'}
            elif days_left >= 7:
                return {'status': 'safe', 'reason': 'Good for donation'}
            elif days_left >= 3:
                return {'status': 'consume_soon', 'reason': 'Eat within 3 days'}
            else:
                return {'status': 'reject', 'reason': 'Too close to expiry'}
        except:
            return {'status': 'safe', 'reason': 'Default - needs checking'}

ai = FoodSafetyAI()

# ========== DATABASE SETUP ==========
def setup_database():
    """Create tables and add sample data"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print(f"✅ Database created: {DATABASE_PATH}")
            
            # Add sample organizations
            if Organization.query.count() == 0:
                orgs = [
                    Organization(
                        name="City Food Bank",
                        address="123 Main St, New York",
                        lat=40.7128,
                        lng=-74.0060,
                        phone="555-0101",
                        email="info@foodbank.org"
                    ),
                    Organization(
                        name="Community Kitchen",
                        address="456 Oak Ave, Brooklyn",
                        lat=40.6782,
                        lng=-73.9442,
                        phone="555-0102",
                        email="help@kitchen.org"
                    )
                ]
                db.session.add_all(orgs)
                print(f"✅ Added {len(orgs)} organizations")
            
            # Add sample food donations
            if FoodListing.query.count() == 0:
                today = datetime.now().date()
                foods = [
                    FoodListing(
                        food_name="Fresh Apples",
                        quantity=20,
                        expiry_date=(today + timedelta(days=10)).isoformat(),
                        location="Central Market",
                        lat=40.7140,
                        lng=-74.0080,
                        ai_status="safe",
                        ai_reason="Fresh produce"
                    ),
                    FoodListing(
                        food_name="Bread Loaves",
                        quantity=15,
                        expiry_date=(today + timedelta(days=2)).isoformat(),
                        location="Downtown Bakery",
                        lat=40.7589,
                        lng=-73.9851,
                        ai_status="consume_soon",
                        ai_reason="Eat within 2 days"
                    ),
                    FoodListing(
                        food_name="Canned Soup",
                        quantity=30,
                        expiry_date=(today + timedelta(days=365)).isoformat(),
                        location="Supermarket",
                        lat=40.7831,
                        lng=-73.9712,
                        ai_status="safe",
                        ai_reason="Long shelf life"
                    )
                ]
                db.session.add_all(foods)
                print(f"✅ Added {len(foods)} sample donations")
            
            db.session.commit()
            print("✅ Database setup complete!")
            
        except Exception as e:
            print(f"❌ Database setup error: {e}")
            db.session.rollback()

# Run database setup
setup_database()

# ========== API ROUTES ==========
@app.route('/')
def home():
    return jsonify({
        "message": "Food Donation API",
        "status": "running",
        "endpoints": {
            "/api/donations": "GET/POST food donations",
            "/api/organizations": "GET food banks",
            "/api/ai/classify": "POST check food safety"
        }
    })

@app.route('/api/donations', methods=['GET'])
def get_donations():
    try:
        donations = FoodListing.query.filter_by(status='available').all()
        return jsonify({
            "success": True,
            "count": len(donations),
            "donations": [d.to_dict() for d in donations]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/donations', methods=['POST'])
def create_donation():
    try:
        data = request.json
        
        # Validate
        if not data.get('food_name') or not data.get('expiry_date'):
            return jsonify({"error": "Missing food_name or expiry_date"}), 400
        
        # AI classification
        ai_result = ai.classify(data['food_name'], data['expiry_date'])
        
        # Create donation
        donation = FoodListing(
            food_name=data['food_name'],
            quantity=data.get('quantity', 1),
            expiry_date=data['expiry_date'],
            location=data.get('location', ''),
            lat=data.get('lat'),
            lng=data.get('lng'),
            ai_status=ai_result['status'],
            ai_reason=ai_result['reason'],
            status='available'
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Donation created",
            "donation_id": donation.id,
            "ai_result": ai_result
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/donations/<int:donation_id>/claim', methods=['POST'])
def claim_donation(donation_id):
    try:
        donation = FoodListing.query.get(donation_id)
        if not donation:
            return jsonify({"error": "Donation not found"}), 404
        
        donation.status = 'claimed'
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Donation claimed"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/organizations', methods=['GET'])
def get_organizations():
    try:
        orgs = Organization.query.all()
        return jsonify({
            "success": True,
            "count": len(orgs),
            "organizations": [org.to_dict() for org in orgs]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/classify', methods=['POST'])
def classify_food():
    try:
        data = request.json
        result = ai.classify(data['food_name'], data['expiry_date'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/map-data', methods=['GET'])
def get_map_data():
    try:
        donations = FoodListing.query.filter_by(status='available').all()
        orgs = Organization.query.all()
        
        return jsonify({
            "donations": [
                {"id": d.id, "name": d.food_name, "lat": d.lat, "lng": d.lng, 
                 "status": d.ai_status, "expiry": d.expiry_date}
                for d in donations if d.lat and d.lng
            ],
            "organizations": [
                {"id": o.id, "name": o.name, "lat": o.lat, "lng": o.lng}
                for o in orgs if o.lat and o.lng
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        stats = {
            "total_donations": FoodListing.query.count(),
            "available_donations": FoodListing.query.filter_by(status='available').count(),
            "organizations": Organization.query.count(),
            "ai_safe": FoodListing.query.filter_by(ai_status='safe').count(),
            "ai_consume_soon": FoodListing.query.filter_by(ai_status='consume_soon').count(),
            "ai_reject": FoodListing.query.filter_by(ai_status='reject').count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== RUN APP ==========
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 FOOD DONATION PLATFORM API")
    print("="*50)
    print(f"📊 Database: {DATABASE_PATH}")
    print("🌐 Server: http://localhost:5000")
    print("\n📋 Endpoints:")
    print("  GET  /                     - API info")
    print("  GET  /api/donations        - List donations")
    print("  POST /api/donations        - Create donation")
    print("  GET  /api/organizations    - List food banks")
    print("  POST /api/ai/classify      - AI food check")
    print("  GET  /api/map-data         - Map data")
    print("  GET  /api/stats            - Statistics")
    print("\n✅ Ready! Press Ctrl+C to stop")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False)