# backend/database.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random

db = SQLAlchemy()

class User(db.Model):
    """Users: donors, receivers, admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20), nullable=False)  # donor, receiver, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('FoodListing', backref='donor', lazy=True)
    claimed_donations = db.relationship('DonationTransaction', backref='claimer', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'user_type': self.user_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class FoodListing(db.Model):
    """Food donation listings"""
    __tablename__ = 'food_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Donor info
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    donor_name = db.Column(db.String(100))
    donor_contact = db.Column(db.String(100))
    
    # Food details
    food_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    unit = db.Column(db.String(20), default='items')  # items, kg, liters, boxes
    expiry_date = db.Column(db.Date, nullable=False)
    food_type = db.Column(db.String(50))  # fruits, vegetables, dairy, grains, etc.
    
    # Location
    pickup_address = db.Column(db.Text)
    city = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # AI Classification
    ai_status = db.Column(db.String(50))  # safe_to_donate, consume_soon, reject
    ai_confidence = db.Column(db.Float)
    ai_reason = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='available')  # available, claimed, delivered, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Storage info
    storage = db.Column(db.String(50))  # refrigerated, frozen, pantry
    packaging = db.Column(db.String(50))  # sealed, opened, original
    
    def to_dict(self):
        return {
            'id': self.id,
            'donor': {
                'id': self.donor_id,
                'name': self.donor_name,
                'contact': self.donor_contact
            },
            'food_details': {
                'name': self.food_name,
                'description': self.description,
                'quantity': self.quantity,
                'unit': self.unit,
                'type': self.food_type,
                'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None
            },
            'location': {
                'address': self.pickup_address,
                'city': self.city,
                'coordinates': {
                    'lat': self.latitude,
                    'lng': self.longitude
                }
            },
            'ai_classification': {
                'status': self.ai_status,
                'confidence': self.ai_confidence,
                'reason': self.ai_reason
            },
            'status': self.status,
            'storage': self.storage,
            'packaging': self.packaging,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Organization(db.Model):
    """Food banks, NGOs, shelters"""
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Contact
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    
    # Location
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(50))
    
    # Details
    org_type = db.Column(db.String(50))  # food_bank, shelter, community_center
    capacity = db.Column(db.Integer)  # Storage capacity
    operating_hours = db.Column(db.Text)
    
    # What they accept
    accepts_perishable = db.Column(db.Boolean, default=True)
    accepts_non_perishable = db.Column(db.Boolean, default=True)
    accepts_cooked = db.Column(db.Boolean, default=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'contact': {
                'address': self.address,
                'phone': self.phone,
                'email': self.email,
                'website': self.website
            },
            'location': {
                'lat': self.latitude,
                'lng': self.longitude,
                'city': self.city
            },
            'details': {
                'type': self.org_type,
                'capacity': self.capacity,
                'hours': self.operating_hours,
                'accepts': {
                    'perishable': self.accepts_perishable,
                    'non_perishable': self.accepts_non_perishable,
                    'cooked': self.accepts_cooked
                }
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DonationTransaction(db.Model):
    """Tracks donation claims and deliveries"""
    __tablename__ = 'donation_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    food_listing_id = db.Column(db.Integer, db.ForeignKey('food_listings.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_pickup = db.Column(db.DateTime)
    picked_up_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(20), default='claimed')  # claimed, scheduled, picked_up, delivered, cancelled
    notes = db.Column(db.Text)
    
    # Feedback
    donor_rating = db.Column(db.Integer)  # 1-5
    receiver_rating = db.Column(db.Integer)  # 1-5
    feedback = db.Column(db.Text)
    
    # Relationships
    food_listing = db.relationship('FoodListing', backref='transaction', lazy=True)
    organization = db.relationship('Organization', backref='transactions', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'food_listing_id': self.food_listing_id,
            'organization_id': self.organization_id,
            'claimed_by_id': self.claimed_by_id,
            'timestamps': {
                'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
                'scheduled_pickup': self.scheduled_pickup.isoformat() if self.scheduled_pickup else None,
                'picked_up_at': self.picked_up_at.isoformat() if self.picked_up_at else None,
                'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
            },
            'status': self.status,
            'notes': self.notes,
            'feedback': {
                'donor_rating': self.donor_rating,
                'receiver_rating': self.receiver_rating,
                'comments': self.feedback
            }
        }

class FoodCategory(db.Model):
    """Predefined food categories for better organization"""
    __tablename__ = 'food_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    risk_level = db.Column(db.String(20))  # high, medium, low
    shelf_life_days = db.Column(db.Integer)  # Typical shelf life
    requires_refrigeration = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'risk_level': self.risk_level,
            'shelf_life_days': self.shelf_life_days,
            'requires_refrigeration': self.requires_refrigeration
        }

# Helper Functions
def init_db(app):
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Check if we need to add sample data
        if User.query.count() == 0:
            add_sample_data()
            print("✓ Sample data added")

def add_sample_data():
    """Add realistic sample data for testing"""
    
    # Add food categories
    categories = [
        FoodCategory(name="Dairy", risk_level="high", shelf_life_days=7, requires_refrigeration=True),
        FoodCategory(name="Meat", risk_level="high", shelf_life_days=3, requires_refrigeration=True),
        FoodCategory(name="Seafood", risk_level="high", shelf_life_days=2, requires_refrigeration=True),
        FoodCategory(name="Fruits", risk_level="medium", shelf_life_days=7, requires_refrigeration=False),
        FoodCategory(name="Vegetables", risk_level="medium", shelf_life_days=5, requires_refrigeration=False),
        FoodCategory(name="Bakery", risk_level="medium", shelf_life_days=3, requires_refrigeration=False),
        FoodCategory(name="Canned Goods", risk_level="low", shelf_life_days=365, requires_refrigeration=False),
        FoodCategory(name="Dry Goods", risk_level="low", shelf_life_days=180, requires_refrigeration=False),
        FoodCategory(name="Beverages", risk_level="low", shelf_life_days=365, requires_refrigeration=False),
    ]
    db.session.add_all(categories)
    
    # Add sample users
    users = [
        User(email="restaurant@example.com", name="City Bistro", phone="555-0101", user_type="donor"),
        User(email="bakery@example.com", name="Sweet Treats Bakery", phone="555-0102", user_type="donor"),
        User(email="grocery@example.com", name="FreshMart Grocery", phone="555-0103", user_type="donor"),
        User(email="volunteer@example.com", name="John Smith", phone="555-0201", user_type="receiver"),
        User(email="admin@example.com", name="Admin User", phone="555-0001", user_type="admin"),
    ]
    db.session.add_all(users)
    
    # Add organizations (food banks/NGOs)
    orgs = [
        Organization(
            name="Community Food Bank",
            description="Providing meals to families in need since 2010. We accept all non-expired food items.",
            address="123 Main Street, Cityville",
            phone="(555) 123-4567",
            email="info@communityfoodbank.org",
            website="www.communityfoodbank.org",
            latitude=40.7128,
            longitude=-74.0060,
            city="Cityville",
            org_type="food_bank",
            capacity=5000,
            operating_hours="Mon-Fri: 9AM-5PM, Sat: 10AM-2PM",
            accepts_perishable=True,
            accepts_non_perishable=True,
            accepts_cooked=False
        ),
        Organization(
            name="Hope Kitchen Shelter",
            description="Daily meal service for homeless community. We especially need ready-to-eat items.",
            address="456 Oak Avenue, Townsville",
            phone="(555) 234-5678",
            email="contact@hopekitchen.org",
            latitude=40.7589,
            longitude=-73.9851,
            city="Townsville",
            org_type="shelter",
            capacity=200,
            operating_hours="24/7",
            accepts_perishable=True,
            accepts_non_perishable=True,
            accepts_cooked=True
        ),
        Organization(
            name="Youth Center",
            description="After-school programs providing meals to children from low-income families.",
            address="789 Pine Road, Villagetown",
            phone="(555) 345-6789",
            email="support@youthcenter.org",
            latitude=40.7831,
            longitude=-73.9712,
            city="Villagetown",
            org_type="community_center",
            capacity=1000,
            operating_hours="Mon-Fri: 3PM-8PM, Sat: 10AM-4PM",
            accepts_perishable=True,
            accepts_non_perishable=True,
            accepts_cooked=True
        ),
    ]
    db.session.add_all(orgs)
    
    # Add sample food listings
    today = datetime.utcnow().date()
    
    food_listings = [
        FoodListing(
            donor_id=1,
            donor_name="City Bistro",
            donor_contact="555-0101",
            food_name="Fresh Vegetable Soup",
            description="Homemade vegetable soup, 5 large containers. Prepared today.",
            quantity=5,
            unit="containers",
            expiry_date=today + timedelta(days=3),
            food_type="cooked",
            pickup_address="123 Restaurant Row, Cityville",
            city="Cityville",
            latitude=40.7140,
            longitude=-74.0080,
            ai_status="consume_soon",
            ai_confidence=0.85,
            ai_reason="Cooked food should be consumed within 3 days",
            status="available",
            storage="refrigerated",
            packaging="sealed"
        ),
        FoodListing(
            donor_id=2,
            donor_name="Sweet Treats Bakery",
            donor_contact="555-0102",
            food_name="Assorted Bread and Pastries",
            description="Day-old bread, croissants, and muffins. Still fresh and tasty.",
            quantity=25,
            unit="items",
            expiry_date=today + timedelta(days=2),
            food_type="bakery",
            pickup_address="456 Baker Street, Cityville",
            city="Cityville",
            latitude=40.7160,
            longitude=-74.0100,
            ai_status="consume_soon",
            ai_confidence=0.90,
            ai_reason="Bakery items best consumed within 2 days",
            status="available",
            storage="pantry",
            packaging="packaged"
        ),
        FoodListing(
            donor_id=3,
            donor_name="FreshMart Grocery",
            donor_contact="555-0103",
            food_name="Canned Vegetables and Beans",
            description="Assorted canned goods - corn, beans, tomatoes. 2 cases available.",
            quantity=24,
            unit="cans",
            expiry_date=today + timedelta(days=365),
            food_type="canned_goods",
            pickup_address="789 Market Street, Cityville",
            city="Cityville",
            latitude=40.7180,
            longitude=-74.0120,
            ai_status="safe_to_donate",
            ai_confidence=0.95,
            ai_reason="Canned goods have long shelf life",
            status="available",
            storage="pantry",
            packaging="sealed"
        ),
        FoodListing(
            donor_id=1,
            donor_name="City Bistro",
            donor_contact="555-0101",
            food_name="Fresh Milk and Cheese",
            description="Unopened milk cartons and cheese blocks. From today's delivery.",
            quantity=10,
            unit="items",
            expiry_date=today + timedelta(days=5),
            food_type="dairy",
            pickup_address="123 Restaurant Row, Cityville",
            city="Cityville",
            latitude=40.7140,
            longitude=-74.0080,
            ai_status="safe_to_donate",
            ai_confidence=0.80,
            ai_reason="Dairy products with 5 days until expiry",
            status="available",
            storage="refrigerated",
            packaging="original"
        ),
    ]
    db.session.add_all(food_listings)
    
    # Add a claimed donation for demonstration
    transaction = DonationTransaction(
        food_listing_id=1,
        organization_id=1,
        claimed_by_id=4,
        claimed_at=datetime.utcnow() - timedelta(hours=2),
        scheduled_pickup=datetime.utcnow() + timedelta(days=1),
        status="claimed",
        notes="Will pick up tomorrow morning"
    )
    db.session.add(transaction)
    
    # Update the first listing to claimed
    food_listings[0].status = "claimed"
    
    db.session.commit()
    print(f"✓ Added {len(users)} users, {len(orgs)} organizations, {len(food_listings)} food listings")

def get_db_stats():
    """Get database statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_donations': FoodListing.query.count(),
        'available_donations': FoodListing.query.filter_by(status='available').count(),
        'total_organizations': Organization.query.count(),
        'active_organizations': Organization.query.filter_by(is_active=True).count(),
        'total_transactions': DonationTransaction.query.count()
    }
    return stats

# Quick test in Python shell
from app import app
from database import get_db_stats

with app.app_context():
    stats = get_db_stats()
    print(f"Total donations: {stats['total_donations']}")
    print(f"Available donations: {stats['available_donations']}")
    print(f"Food banks: {stats['total_organizations']}")