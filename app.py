# backend/app.py
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

# ========== API ROUTES ==========

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
        
        # Create donation (AI will be set automatically in __init__)
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
            storage_condition=data.get('storage_condition', ''),
            packaging=data.get('packaging', ''),
            status='available'
        )
        
        db.session.add(donation)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Donation created successfully",
            "donation_id": donation.id,
            "ai_result": {
                "status": donation.ai_status,
                "reason": donation.ai_reason,
                "confidence": donation.ai_confidence
            }
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
            "ai_safe": FoodListing.query.filter_by(ai_status='safe_to_donate').count(),
            "ai_consume_soon": FoodListing.query.filter_by(ai_status='consume_soon').count(),
            "ai_reject": FoodListing.query.filter_by(ai_status='reject').count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/donations/<int:donation_id>/claim', methods=['POST'])
def claim_donation(donation_id):
    """Claim a food donation"""
    try:
        donation = FoodListing.query.get(donation_id)
        if not donation:
            return jsonify({"error": "Donation not found"}), 404
        
        if donation.status != 'available':
            return jsonify({"error": f"Donation is already {donation.status}"}), 400
        
        donation.status = 'claimed'
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Donation claimed successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            }
            
            header {
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #eaeaea;
            }
            
            h1 {
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            
            .tagline {
                color: #7f8c8d;
                font-size: 1.2em;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                border-top: 5px solid #3498db;
                transition: transform 0.3s ease;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-value {
                font-size: 36px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
            
            .stat-label {
                color: #7f8c8d;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .section {
                margin-bottom: 40px;
            }
            
            .section-title {
                color: #2c3e50;
                border-left: 5px solid #3498db;
                padding-left: 15px;
                margin-bottom: 25px;
                font-size: 1.5em;
            }
            
            .upload-box {
                background: #f8f9fa;
                padding: 30px;
                border-radius: 15px;
                border: 2px dashed #bdc3c7;
                text-align: center;
                margin-bottom: 30px;
            }
            
            .upload-box h3 {
                color: #2c3e50;
                margin-bottom: 20px;
            }
            
            .form-group {
                margin-bottom: 20px;
                text-align: left;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #2c3e50;
                font-weight: 500;
            }
            
            input, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            
            input:focus, select:focus {
                outline: none;
                border-color: #3498db;
            }
            
            .file-input {
                padding: 10px;
                border: 2px dashed #3498db;
                background: #f0f8ff;
                cursor: pointer;
            }
            
            .btn {
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin: 5px;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
            }
            
            .btn-success {
                background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            }
            
            .btn-warning {
                background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            }
            
            .food-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                gap: 30px;
            }
            
            .food-card {
                background: white;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
                border: 1px solid #f0f0f0;
            }
            
            .food-card:hover {
                transform: translateY(-10px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.12);
            }
            
            .food-image {
                width: 100%;
                height: 220px;
                object-fit: cover;
                transition: transform 0.5s ease;
            }
            
            .food-card:hover .food-image {
                transform: scale(1.05);
            }
            
            .no-image {
                width: 100%;
                height: 220px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 18px;
            }
            
            .no-image i {
                font-size: 48px;
                margin-bottom: 10px;
            }
            
            .food-info {
                padding: 25px;
            }
            
            .food-name {
                font-size: 1.4em;
                font-weight: 600;
                color: #2c3e50;
                margin: 0 0 10px 0;
            }
            
            .food-description {
                color: #7f8c8d;
                margin-bottom: 15px;
                line-height: 1.5;
            }
            
            .food-details {
                margin: 15px 0;
            }
            
            .detail-item {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                color: #555;
            }
            
            .detail-label {
                font-weight: 500;
                color: #7f8c8d;
            }
            
            .ai-badge {
                display: inline-block;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
            }
            
            .ai-safe { background: #d5f4e6; color: #27ae60; }
            .ai-soon { background: #fef9e7; color: #f39c12; }
            .ai-reject { background: #fdeaea; color: #e74c3c; }
            
            .message {
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                text-align: center;
                font-weight: 500;
            }
            
            .success { background: #d5f4e6; color: #27ae60; border-left: 4px solid #27ae60; }
            .error { background: #fdeaea; color: #e74c3c; border-left: 4px solid #e74c3c; }
            .loading { background: #e3f2fd; color: #1976d2; border-left: 4px solid #1976d2; }
            
            .loading-spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .actions {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            
            .btn-small {
                padding: 8px 15px;
                font-size: 14px;
                flex: 1;
            }
            
            .status-badge {
                position: absolute;
                top: 15px;
                right: 15px;
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }
            
            .status-available { background: #27ae60; }
            .status-claimed { background: #f39c12; }
            .status-expired { background: #e74c3c; }
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1><i class="fas fa-utensils"></i> Food Provider Dashboard</h1>
                <p class="tagline">Manage your food donations and reduce waste</p>
            </header>
            
            <div class="stats-grid" id="stats-container">
                <div class="stat-card">
                    <div class="stat-value" id="total-donations">0</div>
                    <div class="stat-label">Total Donations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="available-donations">0</div>
                    <div class="stat-label">Available Now</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="donations-with-images">0</div>
                    <div class="stat-label">With Images</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="ai-safe">0</div>
                    <div class="stat-label">AI Approved</div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title"><i class="fas fa-cloud-upload-alt"></i> Upload New Donation</h2>
                <div class="upload-box">
                    <form id="donationForm">
                        <div class="form-group">
                            <label for="foodName"><i class="fas fa-apple-alt"></i> Food Name *</label>
                            <input type="text" id="foodName" placeholder="e.g., Fresh Apples, Bread Loaves" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="description"><i class="fas fa-align-left"></i> Description</label>
                            <input type="text" id="description" placeholder="Brief description of the food">
                        </div>
                        
                        <div class="form-group">
                            <label for="quantity"><i class="fas fa-balance-scale"></i> Quantity</label>
                            <input type="number" id="quantity" value="1" min="1">
                        </div>
                        
                        <div class="form-group">
                            <label for="expiryDate"><i class="fas fa-calendar-alt"></i> Expiry Date *</label>
                            <input type="date" id="expiryDate" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="imageUpload"><i class="fas fa-camera"></i> Food Image</label>
                            <input type="file" id="imageUpload" class="file-input" accept="image/*">
                        </div>
                        
                        <button type="button" onclick="createDonation()" class="btn btn-success">
                            <i class="fas fa-plus-circle"></i> Create Donation
                        </button>
                    </form>
                </div>
                <div id="createMessage"></div>
            </div>
            
            <div class="section">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 class="section-title"><i class="fas fa-list"></i> Available Donations</h2>
                    <div>
                        <button onclick="loadDonations()" class="btn">
                            <i class="fas fa-sync-alt"></i> Refresh
                        </button>
                        <button onclick="uploadImageToExisting()" class="btn btn-warning">
                            <i class="fas fa-image"></i> Add Image to Existing
                        </button>
                    </div>
                </div>
                
                <div id="uploadExistingSection" style="display: none; margin-bottom: 20px;">
                    <div class="upload-box">
                        <h3><i class="fas fa-upload"></i> Add Image to Existing Donation</h3>
                        <input type="number" id="existingDonationId" placeholder="Enter Donation ID" style="width: 200px; margin-right: 10px;">
                        <input type="file" id="existingImageUpload" accept="image/*" style="display: inline-block;">
                        <button onclick="uploadToExisting()" class="btn">Upload</button>
                        <button onclick="hideUploadSection()" class="btn" style="background: #95a5a6;">Cancel</button>
                        <div id="existingUploadMessage" style="margin-top: 10px;"></div>
                    </div>
                </div>
                
                <div id="donations-container">
                    <!-- Donations will load here -->
                </div>
            </div>
        </div>

        <script>
            const API_BASE = 'http://localhost:5000/api';
            
            // Format date for input field
            function formatDateForInput(date) {
                const d = new Date(date);
                const year = d.getFullYear();
                const month = String(d.getMonth() + 1).padStart(2, '0');
                const day = String(d.getDate() + 2).padStart(2, '0');
                return `${year}-${month}-${day}`;
            }
            
            // Set default expiry date (tomorrow)
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('expiryDate').value = formatDateForInput(new Date());
                loadStats();
                loadDonations();
            });
            
            // Load statistics
            async function loadStats() {
                try {
                    const response = await fetch(`${API_BASE}/stats`);
                    const stats = await response.json();
                    
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
                    container.innerHTML = '<div class="loading-spinner"></div><div class="loading">Loading donations...</div>';
                    
                    const response = await fetch(`${API_BASE}/donations/images`);
                    const data = await response.json();
                    
                    if (!data.success) throw new Error(data.error);
                    
                    displayDonations(data.donations);
                    loadStats(); // Refresh stats
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('donations-container').innerHTML = 
                        '<div class="error">Error loading donations. Make sure backend is running on port 5000.</div>';
                }
            }
            
            function displayDonations(donations) {
                const container = document.getElementById('donations-container');
                
                if (!donations || donations.length === 0) {
                    container.innerHTML = '<div class="message">No food donations available yet. Create your first donation!</div>';
                    return;
                }
                
                container.innerHTML = donations.map(donation => {
                    const aiClass = donation.ai_classification?.status || 'safe_to_donate';
                    const aiStatus = aiClass === 'safe_to_donate' ? 'safe' : 
                                     aiClass === 'consume_soon' ? 'soon' : 'reject';
                    
                    return `
                        <div class="food-card">
                            <div style="position: relative;">
                                ${donation.image_url 
                                    ? `<img src="${donation.image_url}" alt="${donation.food_name}" class="food-image">`
                                    : `<div class="no-image">
                                        <i class="fas fa-camera"></i>
                                        <span>No Image Available</span>
                                       </div>`
                                }
                                <div class="status-badge status-${donation.status}">
                                    ${donation.status.toUpperCase()}
                                </div>
                            </div>
                            <div class="food-info">
                                <h3 class="food-name">${donation.food_name}</h3>
                                ${donation.description ? `<p class="food-description">${donation.description}</p>` : ''}
                                
                                <div class="food-details">
                                    <div class="detail-item">
                                        <span class="detail-label">Quantity:</span>
                                        <span>${donation.quantity} ${donation.unit}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Expires:</span>
                                        <span>${donation.expiry_date}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Donor:</span>
                                        <span>${donation.donor_name || 'Anonymous'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">Location:</span>
                                        <span>${donation.location?.address || 'Not specified'}</span>
                                    </div>
                                </div>
                                
                                <div class="ai-badge ai-${aiStatus}">
                                    <i class="fas fa-robot"></i> AI: ${aiClass.replace('_', ' ').toUpperCase()}
                                </div>
                                
                                <div class="actions">
                                    <button onclick="claimDonation(${donation.id})" class="btn btn-small" ${donation.status !== 'available' ? 'disabled style="opacity:0.5"' : ''}>
                                        <i class="fas fa-check"></i> ${donation.status === 'available' ? 'Claim' : 'Claimed'}
                                    </button>
                                    <button onclick="showUploadForDonation(${donation.id})" class="btn btn-small btn-warning">
                                        <i class="fas fa-image"></i> Add Image
                                    </button>
                                </div>
                                
                                <p style="margin-top: 15px; font-size: 12px; color: #aaa;">
                                    ID: ${donation.id} • Created: ${new Date(donation.created_at).toLocaleDateString()}
                                </p>
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            // Create new donation
            async function createDonation() {
                const foodName = document.getElementById('foodName').value;
                const description = document.getElementById('description').value;
                const quantity = document.getElementById('quantity').value;
                const expiryDate = document.getElementById('expiryDate').value;
                const imageFile = document.getElementById('imageUpload').files[0];
                
                if (!foodName || !expiryDate) {
                    showMessage('error', 'Please fill in all required fields (Food Name and Expiry Date)');
                    return;
                }
                
                try {
                    showMessage('loading', 'Creating donation...');
                    
                    // Create donation data
                    const donationData = {
                        food_name: foodName,
                        description: description,
                        quantity: parseInt(quantity),
                        expiry_date: expiryDate,
                        donor_name: "Your Restaurant", // You can change this
                        donor_contact: "contact@example.com",
                        unit: "items",
                        status: "available"
                    };
                    
                    const response = await fetch(`${API_BASE}/donations`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(donationData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showMessage('success', '✅ Donation created successfully!');
                        
                        // If image was selected, upload it
                        if (imageFile && result.donation_id) {
                            await uploadImage(result.donation_id, imageFile);
                        }
                        
                        // Clear form and refresh
                        document.getElementById('donationForm').reset();
                        document.getElementById('expiryDate').value = formatDateForInput(new Date());
                        setTimeout(loadDonations, 1500);
                    } else {
                        showMessage('error', `❌ ${result.error}`);
                    }
                } catch (error) {
                    console.error('Create error:', error);
                    showMessage('error', '❌ Failed to create donation');
                }
            }
            
            // Upload image to donation
            async function uploadImage(donationId, imageFile) {
                const formData = new FormData();
                formData.append('image', imageFile);
                
                try {
                    const response = await fetch(`${API_BASE}/donations/${donationId}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    return result.success;
                } catch (error) {
                    console.error('Image upload error:', error);
                    return false;
                }
            }
            
            // Claim donation
            async function claimDonation(donationId) {
                if (!confirm('Are you sure you want to claim this donation?')) return;
                
                try {
                    const response = await fetch(`${API_BASE}/donations/${donationId}/claim`, {
                        method: 'POST'
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert('✅ Donation claimed successfully!');
                        loadDonations();
                    } else {
                        alert(`❌ ${result.error}`);
                    }
                } catch (error) {
                    console.error('Claim error:', error);
                    alert('❌ Failed to claim donation');
                }
            }
            
            // Show upload section for existing donation
            function showUploadForDonation(donationId) {
                document.getElementById('uploadExistingSection').style.display = 'block';
                document.getElementById('existingDonationId').value = donationId;
            }
            
            function uploadImageToExisting() {
                document.getElementById('uploadExistingSection').style.display = 'block';
            }
            
            function hideUploadSection() {
                document.getElementById('uploadExistingSection').style.display = 'none';
            }
            
            // Upload to existing donation
            async function uploadToExisting() {
                const donationId = document.getElementById('existingDonationId').value;
                const imageFile = document.getElementById('existingImageUpload').files[0];
                const messageDiv = document.getElementById('existingUploadMessage');
                
                if (!donationId || !imageFile) {
                    messageDiv.innerHTML = '<div class="error">Please enter donation ID and select an image</div>';
                    return;
                }
                
                try {
                    messageDiv.innerHTML = '<div class="loading">Uploading image...</div>';
                    
                    const formData = new FormData();
                    formData.append('image', imageFile);
                    
                    const response = await fetch(`${API_BASE}/donations/${donationId}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = '<div class="success">✅ Image uploaded successfully!</div>';
                        // Clear and hide
                        setTimeout(() => {
                            hideUploadSection();
                            document.getElementById('existingDonationId').value = '';
                            document.getElementById('existingImageUpload').value = '';
                            loadDonations();
                        }, 1500);
                    } else {
                        messageDiv.innerHTML = `<div class="error">❌ ${result.error}</div>`;
                    }
                } catch (error) {
                    console.error('Upload error:', error);
                    messageDiv.innerHTML = '<div class="error">❌ Upload failed</div>';
                }
            }
            
            // Helper function to show messages
            function showMessage(type, text) {
                const div = document.getElementById('createMessage');
                div.innerHTML = `<div class="message ${type}">${text}</div>`;
                setTimeout(() => {
                    div.innerHTML = '';
                }, 5000);
            }
        </script>
    </body>
    </html>
    '''

# Run the application
if __name__ == '__main__':
    # Initialize database with sample data
    with app.app_context():
        init_db(app)
    
    print("\n" + "="*60)
    print("🚀 FOOD DONATION PLATFORM")
    print("="*60)
    print(f"📊 Database: {DATABASE_PATH}")
    print("🌐 API Server: http://localhost:5000")
    print("📱 Provider Dashboard: http://localhost:5000/provider")
    print("\n📋 Available Endpoints:")
    print("  GET  /                             - API information")
    print("  GET  /api/donations                - List all donations")
    print("  GET  /api/donations/images         - Donations with images")
    print("  POST /api/donations                - Create new donation")
    print("  POST /api/donations/{id}/upload-image - Upload image")
    print("  POST /api/donations/{id}/claim     - Claim donation")
    print("  GET  /api/organizations            - List food banks")
    print("  GET  /api/stats                    - Platform statistics")
    print("\n✅ Ready! Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False)
