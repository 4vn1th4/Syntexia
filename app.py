from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, init_db, FoodListing, Organization, User, DonationTransaction

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'food_donation.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'food-donation-secret-key-2024'

# Image upload configuration
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Initialize database
db.init_app(app)
init_db(app)

# Simple AI Classifier
class FoodSafetyAI:
    def classify(self, food_name, expiry_date_str, description=""):
        """Simple AI food safety classifier"""
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            days_left = (expiry_date - datetime.now().date()).days
            
            if days_left < 0:
                return {'status': 'reject', 'confidence': 0.95, 'reason': 'Food is expired'}
            elif days_left <= 2:
                return {'status': 'consume_soon', 'confidence': 0.85, 'reason': f'Best consumed within {days_left} days'}
            elif days_left <= 7:
                return {'status': 'safe', 'confidence': 0.75, 'reason': 'Good for donation, use soon'}
            else:
                return {'status': 'safe', 'confidence': 0.95, 'reason': 'Excellent for donation'}
        except:
            return {'status': 'safe', 'confidence': 0.5, 'reason': 'Default classification'}

ai = FoodSafetyAI()

# API Routes
@app.route('/')
def home():
    return jsonify({
        "message": "Food Donation Platform API",
        "version": "1.0",
        "endpoints": {
            "/api/donations": "GET/POST food donations",
            "/api/donations/images": "GET donations with images",
            "/api/donations/<id>/upload-image": "POST upload image",
            "/api/organizations": "GET food banks",
            "/api/stats": "GET platform statistics",
            "/provider": "Provider dashboard"
        }
    })

@app.route('/api/donations', methods=['GET'])
def get_donations():
    """Get all available food donations"""
    try:
        status = request.args.get('status', 'available')
        donations = FoodListing.query.filter_by(status=status).all()
        return jsonify({
            "success": True,
            "count": len(donations),
            "donations": [d.to_dict() for d in donations]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/donations/images', methods=['GET'])
def get_donations_with_images():
    """Get donations specifically for image display"""
    try:
        donations = FoodListing.query.filter_by(status='available').all()
        result = []
        for donation in donations:
            data = donation.to_dict()
            data['has_image'] = bool(donation.image_url)
            result.append(data)
        
        return jsonify({
            "success": True,
            "count": len(result),
            "donations": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/donations', methods=['POST'])
def create_donation():
    """Create a new food donation"""
    try:
        data = request.json
        
        # Required fields validation
        required_fields = ['food_name', 'expiry_date', 'donor_name']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # AI classification
        ai_result = ai.classify(
            data['food_name'],
            data['expiry_date'],
            data.get('description', '')
        )
        
        # Create donation
        donation = FoodListing(
            donor_name=data['donor_name'],
            donor_contact=data.get('donor_contact', ''),
            food_name=data['food_name'],
            description=data.get('description', ''),
            quantity=data.get('quantity', 1),
            unit=data.get('unit', 'items'),
            expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date(),
            food_type=data.get('food_type', ''),
            location_lat=data.get('lat'),
            location_lng=data.get('lng'),
            address=data.get('address', ''),
            image_url=data.get('image_url', ''),
            ai_status=ai_result['status'],
            ai_confidence=ai_result['confidence'],
            ai_reason=ai_result['reason'],
            storage_condition=data.get('storage_condition', ''),
            packaging=data.get('packaging', '')
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Donation created successfully",
            "donation_id": donation.id,
            "ai_result": ai_result
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/donations/<int:donation_id>/upload-image', methods=['POST'])
def upload_donation_image(donation_id):
    """Upload an image for a donation"""
    try:
        donation = FoodListing.query.get(donation_id)
        if not donation:
            return jsonify({"error": "Donation not found"}), 404
        
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"donation_{donation_id}_{timestamp}.{ext}"
            
            # Save file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Update donation
            donation.image_url = f'/static/uploads/{filename}'
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Image uploaded successfully",
                "image_url": donation.image_url
            })
        
        return jsonify({"error": "Invalid file type"}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/organizations', methods=['GET'])
def get_organizations():
    """Get all food banks/organizations"""
    try:
        organizations = Organization.query.filter_by(is_active=True).all()
        return jsonify({
            "success": True,
            "count": len(organizations),
            "organizations": [org.to_dict() for org in organizations]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get platform statistics"""
    try:
        stats = {
            "total_donations": FoodListing.query.count(),
            "available_donations": FoodListing.query.filter_by(status='available').count(),
            "claimed_donations": FoodListing.query.filter_by(status='claimed').count(),
            "delivered_donations": FoodListing.query.filter_by(status='delivered').count(),
            "organizations_count": Organization.query.filter_by(is_active=True).count(),
            "donations_with_images": FoodListing.query.filter(FoodListing.image_url != '').count(),
            "ai_safe": FoodListing.query.filter_by(ai_status='safe').count(),
            "ai_consume_soon": FoodListing.query.filter_by(ai_status='consume_soon').count(),
            "ai_reject": FoodListing.query.filter_by(ai_status='reject').count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/classify', methods=['POST'])
def classify_food():
    """AI food safety classification"""
    try:
        data = request.json
        result = ai.classify(
            data['food_name'],
            data['expiry_date'],
            data.get('description', '')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Provider Dashboard HTML
@app.route('/provider')
def provider_dashboard():
    """Provider dashboard HTML page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Food Provider Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border-left: 5px solid #667eea;
            }
            
            .stat-value {
                font-size: 32px;
                font-weight: bold;
                color: #333;
            }
            
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
            
            .section-title {
                color: #444;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            
            .food-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 25px;
            }
            
            .food-card {
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid #eee;
            }
            
            .food-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(0,0,0,0.15);
            }
            
            .food-image {
                width: 100%;
                height: 200px;
                object-fit: cover;
            }
            
            .no-image {
                width: 100%;
                height: 200px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 18px;
            }
            
            .food-info {
                padding: 20px;
            }
            
            .food-name {
                font-size: 20px;
                font-weight: bold;
                margin: 0 0 10px 0;
                color: #333;
            }
            
            .food-detail {
                margin: 8px 0;
                color: #666;
                font-size: 14px;
            }
            
            .ai-status {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
            }
            
            .safe { background: #d4edda; color: #155724; }
            .consume_soon { background: #fff3cd; color: #856404; }
            .reject { background: #f8d7da; color: #721c24; }
            
            .upload-section {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 12px;
                margin-bottom: 30px;
                border: 2px dashed #ddd;
            }
            
            input, button {
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
            }
            
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                cursor: pointer;
                transition: opacity 0.3s;
            }
            
            button:hover {
                opacity: 0.9;
            }
            
            .message {
                padding: 10px;
                border-radius: 8px;
                margin-top: 10px;
                text-align: center;
            }
            
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .loading { background: #d1ecf1; color: #0c5460; }
            
            .refresh-btn {
                background: #28a745;
                float: right;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🥗 Food Provider Dashboard</h1>
                <p>Manage your food donations and images</p>
            </header>
            
            <div class="stats" id="stats-container">
                <div class="stat-card">
                    <div class="stat-value" id="total-donations">0</div>
                    <div class="stat-label">Total Donations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="available-donations">0</div>
                    <div class="stat-label">Available</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="donations-with-images">0</div>
                    <div class="stat-label">With Images</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="ai-safe">0</div>
                    <div class="stat-label">AI Safe</div>
                </div>
            </div>
            
            <div class="upload-section">
                <h2 class="section-title">📤 Upload Food Image</h2>
                <input type="number" id="donationId" placeholder="Enter Donation ID" style="width: 200px;">
                <input type="file" id="imageInput" accept="image/*">
                <button onclick="uploadImage()">Upload Image</button>
                <div id="uploadMessage" class="message"></div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2 class="section-title">🍎 Available Food Donations</h2>
                <button onclick="loadDonations()" class="refresh-btn">🔄 Refresh List</button>
            </div>
            
            <div id="donations-container" class="food-grid">
                <!-- Donations will load here -->
            </div>
        </div>

        <script>
            const API_BASE = 'http://localhost:5000/api';
            
            // Load statistics
            async function loadStats() {
                try {
                    const response = await fetch(`${API_BASE}/stats`);
                    const stats = await response.json();
                    
                    if (!response.ok) throw new Error(stats.error);
                    
                    document.getElementById('total-donations').textContent = stats.total_donations || 0;
                    document.getElementById('available-donations').textContent = stats.available_donations || 0;
                    document.getElementById('donations-with-images').textContent = stats.donations_with_images || 0;
                    document.getElementById('ai-safe').textContent = stats.ai_safe || 0;
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }
            
            // Load donations
            async function loadDonations() {
                try {
                    const container = document.getElementById('donations-container');
                    container.innerHTML = '<div class="loading message">Loading donations...</div>';
                    
                    const response = await fetch(`${API_BASE}/donations/images`);
                    const data = await response.json();
                    
                    if (!data.success) throw new Error(data.error);
                    
                    displayDonations(data.donations);
                    loadStats(); // Refresh stats
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('donations-container').innerHTML = 
                        '<div class="error message">Error loading donations. Check if backend is running.</div>';
                }
            }
            
            function displayDonations(donations) {
                const container = document.getElementById('donations-container');
                
                if (!donations || donations.length === 0) {
                    container.innerHTML = '<div class="message">No food donations available.</div>';
                    return;
                }
                
                container.innerHTML = donations.map(donation => `
                    <div class="food-card">
                        ${donation.image_url 
                            ? `<img src="${donation.image_url}" alt="${donation.food_name}" class="food-image">`
                            : `<div class="no-image">📷 No Image</div>`
                        }
                        <div class="food-info">
                            <h3 class="food-name">${donation.food_name}</h3>
                            <p class="food-detail">📍 ${donation.location?.address || donation.donor_name || 'Location not set'}</p>
                            <p class="food-detail">📅 Expires: ${donation.expiry_date || 'Unknown'}</p>
                            <p class="food-detail">📦 Quantity: ${donation.quantity} ${donation.unit}</p>
                            <p class="food-detail">👤 Donor: ${donation.donor_name || 'Anonymous'}</p>
                            
                            <div class="ai-status ${donation.ai_classification?.status || 'safe'}">
                                AI: ${(donation.ai_classification?.status || 'safe').toUpperCase()}
                            </div>
                            
                            <p style="margin-top: 15px; font-size: 12px; color: #888;">
                                ID: ${donation.id} • ${new Date(donation.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    </div>
                `).join('');
            }
            
            // Upload image
            async function uploadImage() {
                const donationId = document.getElementById('donationId').value;
                const fileInput = document.getElementById('imageInput');
                const messageDiv = document.getElementById('uploadMessage');
                
                if (!donationId) {
                    messageDiv.innerHTML = '<div class="error">Please enter a donation ID</div>';
                    return;
                }
                
                if (!fileInput.files[0]) {
                    messageDiv.innerHTML = '<div class="error">Please select an image file</div>';
                    return;
                }
                
                const formData = new FormData();
                formData.append('image', fileInput.files[0]);
                
                try {
                    messageDiv.innerHTML = '<div class="loading">Uploading image...</div>';
                    
                    const response = await fetch(`${API_BASE}/donations/${donationId}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = '<div class="success">✅ Image uploaded successfully!</div>';
                        // Clear form and refresh
                        fileInput.value = '';
                        document.getElementById('donationId').value = '';
                        setTimeout(loadDonations, 1500);
                    } else {
                        messageDiv.innerHTML = `<div class="error">❌ ${result.error}</div>`;
                    }
                } catch (error) {
                    console.error('Upload error:', error);
                    messageDiv.innerHTML = '<div class="error">❌ Upload failed. Check console.</div>';
                }
            }
            
            // Load data on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadStats();
                loadDonations();
            });
        </script>
    </body>
    </html>
    '''

# Run the application
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 FOOD DONATION PLATFORM")
    print("="*60)
    print(f"📊 Database: {DATABASE_PATH}")
    print("🌐 API: http://localhost:5000")
    print("📱 Provider Dashboard: http://localhost:5000/provider")
    print("\n📋 Available Endpoints:")
    print("  GET  /                     - API information")
    print("  GET  /api/donations        - List all donations")
    print("  GET  /api/donations/images - Donations with images")
    print("  POST /api/donations        - Create new donation")
    print("  POST /api/donations/{id}/upload-image - Upload image")
    print("  GET  /api/organizations    - List food banks")
    print("  GET  /api/stats            - Platform statistics")
    print("  POST /api/ai/classify      - AI food safety check")
    print("  GET  /provider             - Provider dashboard")
    print("\n✅ Ready! Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False)
