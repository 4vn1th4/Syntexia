# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for donors and receivers"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20), nullable=False)  # 'donor', 'receiver', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    donations = db.relationship('FoodListing', backref='donor', lazy=True)
    
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
    
    # Donor information
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    donor_name = db.Column(db.String(100))  # Cache for quick access
    donor_contact = db.Column(db.String(100))
    
    # Food details
    food_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit = db.Column(db.String(20), default='items')  # items, kg, liters, etc.
    expiry_date = db.Column(db.Date, nullable=False)
    food_type = db.Column(db.String(50))  # fruits, vegetables, dairy, etc.
    
    # Location
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    address = db.Column(db.Text)
    
    # AI Classification
    ai_status = db.Column(db.String(50))  # safe_to_donate, consume_soon, reject
    ai_confidence = db.Column(db.Float)
    ai_reason = db.Column(db.Text)
    
    # Status tracking
    status = db.Column(db.String(20), default='available')  # available, claimed, delivered, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Storage information
    storage_condition = db.Column(db.String(50)) #refrigerated, frozen, pantry
    packaging = db.Column(db.String(50))  # sealed, open, original
    
    # Relationships
    transactions = db.relationship('DonationTransaction', backref='food_listing', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default AI classification if not provided
        if not self.ai_status and self.expiry_date:
            from backend.ai_classifier import FoodSafetyClassifier
            classifier = FoodSafetyClassifier()
            result = classifier.predict(
                food_name=self.food_name,
                expiry_date=self.expiry_date.isoformat(),
                description=self.description or ""
            )
            self.ai_status = result['status']
            self.ai_confidence = result.get('confidence', 0.5)
            self.ai_reason = result.get('reason', '')
    
    def to_dict(self):
        return {
            'id': self.id,
            'donor_id': self.donor_id,
            'donor_name': self.donor_name,
            'food_name': self.food_name,
            'description': self.description,
            'quantity': self.quantity,
            'unit': self.unit,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'food_type': self.food_type,
            'location': {
                'lat': self.location_lat,
                'lng': self.location_lng,
                'address': self.address
            },
            'ai_classification': {
                'status': self.ai_status,
                'confidence': self.ai_confidence,
                'reason': self.ai_reason
            },
            'status': self.status,
            'storage_condition': self.storage_condition,
            'packaging': self.packaging,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'days_until_expiry': (self.expiry_date - datetime.utcnow().date()).days if self.expiry_date else None
        }
    
    def is_expired(self):
        """Check if food is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.utcnow().date()
    
    def update_status(self):
        """Automatically update status based on expiry"""
        if self.is_expired() and self.status == 'available':
            self.status = 'expired'
            return True
        return False

class Organization(db.Model):
    """Food banks, NGOs, and other receiving organizations"""
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Contact information
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    
    # Location for mapping
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # Organization details
    org_type = db.Column(db.String(50))  # food_bank, shelter, community_center
    capacity = db.Column(db.Integer)  # Storage capacity
    operating_hours = db.Column(db.Text)
    requirements = db.Column(db.Text)  # What types of food they accept
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('DonationTransaction', backref='organization', lazy=True)
    
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
                'lng': self.longitude
            },
            'details': {
                'type': self.org_type,
                'capacity': self.capacity,
                'operating_hours': self.operating_hours,
                'requirements': self.   rements
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DonationTransaction(db.Model):
    """Track donation claims and deliveries"""
    __tablename__ = 'donation_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    food_listing_id = db.Column(db.Integer, db.ForeignKey('food_listings.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    
    # Timing
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_pickup = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Status tracking
    status = db.Column(db.String(20), default='claimed')  # claimed, picked_up, delivered, cancelled
    notes = db.Column(db.Text)
    
    # Feedback
    donor_feedback = db.Column(db.Text)
    receiver_feedback = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-5 stars
    
    def to_dict(self):
        return {
            'id': self.id,
            'food_listing_id': self.food_listing_id,
            'receiver_id': self.receiver_id,
            'receiver_name': self.organization.name if self.organization else None,
            'status': self.status,
            'timing': {
                'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
                'scheduled_pickup': self.scheduled_pickup.isoformat() if self.scheduled_pickup else None,
                'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
            },
            'notes': self.notes,
            'feedback': {
                'donor': self.donor_feedback,
                'receiver': self.receiver_feedback,
                'rating': self.rating
            }
        }

# Helper function to initialize database
def init_db():
    """Initialize the database with sample data"""
    db.create_all()
    
    # Add sample data if database is empty
    if Organization.query.count() == 0:
        sample_org = Organization(
            name="Community Food Bank",
            description="Providing meals to those in need since 2010",
            address="123 Main Street, Cityville",
            phone="(555) 123-4567",
            email="info@communityfoodbank.org",
            latitude=40.7128,
            longitude=-74.0060,
            org_type="food_bank",
            capacity=5000,
            operating_hours="Mon-Fri: 9AM-5PM, Sat: 10AM-2PM"
        )
        db.session.add(sample_org)
        db.session.commit()