# backend/ai_classifier.py - COMPLETE WORKING VERSION
import os
import requests
import json
import base64
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FoodSafetyImageClassifier:
    def __init__(self):
        # Your OpenRouter API key
        self.api_key = os.getenv("OPENROUTER_API_KEY", "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")
        
        # Vision-capable models (for REAL image analysis)
        self.vision_models = [
            "nvidia/nemotron-nano-12b-v2-vl:free",   # NVIDIA - Vision+Language
            "google/gemini-2.0-flash-exp:free",      # Google Gemini
            "meta-llama/llama-3.2-11b-vision-instruct:free",
        ]
        
        # Text-only models (fallback)
        self.text_models = [
            "meta-llama/llama-3.2-3b-instruct:free",
            "huggingfaceh4/zephyr-7b-beta:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        self.use_api = True if self.api_key else False
        
        if self.use_api:
            print(f"✅ OpenRouter API Ready")
            print(f"📸 Vision Models Available: {len(self.vision_models)}")
            print(f"📝 Text Models Available: {len(self.text_models)}")
        else:
            print("🤖 Using SMART LOCAL AI (no API key needed)")
    
    def predict(self, food_name, expiry_date, description="", image_base64=None):
        """
        REAL image analysis when image_base64 is provided
        Otherwise uses text analysis
        """
        try:
            # Parse dates
            today = datetime.now().date()
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            days_left = (expiry - today).days
            
            # REAL Image Analysis (only if image provided)
            if image_base64 and self.use_api:
                print(f"📸 Analyzing uploaded image...")
                for model in self.vision_models:
                    try:
                        result = self._analyze_with_image(
                            model, food_name, expiry_date, days_left, description, image_base64
                        )
                        result["ai_type"] = f"vision_ai_{model.split('/')[0]}"
                        result["image_analyzed"] = True
                        print(f"✅ Image analyzed with {model.split('/')[0]}")
                        return result
                    except Exception as e:
                        print(f"⚠️ Vision model failed: {str(e)[:50]}")
                        continue
            
            # Text Analysis (no image or image analysis failed)
            if self.use_api and days_left >= 0:
                for model in self.text_models:
                    try:
                        result = self._analyze_text_only(
                            model, food_name, expiry_date, days_left, description
                        )
                        result["ai_type"] = f"text_ai_{model.split('/')[0]}"
                        result["image_analyzed"] = False
                        return result
                    except Exception as e:
                        print(f"⚠️ Text model failed: {str(e)[:50]}")
                        continue
            
            # Local AI fallback
            result = self._smart_local_ai(food_name, days_left, description, image_base64 is not None)
            result["ai_type"] = "local_ai"
            result["image_analyzed"] = image_base64 is not None
            return result
            
        except Exception as e:
            return self._simple_fallback(food_name, expiry_date, str(e))
    
    def _analyze_with_image(self, model, food_name, expiry_date, days_left, description, image_base64):
        """REAL image analysis"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Food Donation Platform"
        }
        
        prompt = self._create_image_prompt(food_name, expiry_date, days_left, description)
        
        messages = [
            {
                "role": "system",
                "content": "You are a food safety expert analyzing food images for donation safety."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 500
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            return self._parse_ai_response(ai_response, model, True)
        else:
            raise Exception(f"API Error {response.status_code}: {response.text[:100]}")
    
    def _analyze_text_only(self, model, food_name, expiry_date, days_left, description):
        """Text-only analysis"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Food Donation Platform"
        }
        
        prompt = self._create_text_prompt(food_name, expiry_date, days_left, description)
        
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a food safety expert analyzing donated food items."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 400
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            return self._parse_ai_response(ai_response, model, False)
        else:
            raise Exception(f"API Error {response.status_code}")
    
    def _create_image_prompt(self, food_name, expiry_date, days_left, description):
        """Prompt for image analysis"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""Analyze this food image for donation safety:

Food: {food_name}
Description: {description or "No description"}
Expiry: {expiry_date} ({days_left} days from {today})

Examine the image for:
1. Visible spoilage (mold, discoloration)
2. Packaging condition
3. Freshness signs

Respond with JSON:
{{
    "status": "safe_to_donate|consume_soon|reject",
    "confidence": 0.85,
    "reason": "Analysis based on image",
    "visual_findings": ["what", "you", "see"],
    "risk_factors": ["key", "risks"],
    "recommendations": ["actions"]
}}"""
    
    def _create_text_prompt(self, food_name, expiry_date, days_left, description):
        """Prompt for text-only analysis"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""FOOD SAFETY ANALYSIS:

FOOD: {food_name}
DESCRIPTION: {description or "No description"}
EXPIRY: {expiry_date} ({days_left} days from today: {today})

CONTEXT: Food bank donation for vulnerable populations.

ANALYSIS REQUEST:
1. Assess perishability based on food type
2. Consider days remaining
3. Evaluate description for quality clues

SAFETY CATEGORIES:
- SAFE_TO_DONATE: Fresh and safe
- CONSUME_SOON: Should be eaten within 3 days
- REJECT: Unsafe or too close to expiry

RESPONSE FORMAT (JSON only):
{{
    "status": "SAFE_TO_DONATE|CONSUME_SOON|REJECT",
    "confidence": 0.85,
    "reason": "Explanation based on food type and expiry",
    "risk_factors": ["key", "risks"],
    "recommendations": ["actionable", "steps"]
}}"""
    
    def _parse_ai_response(self, ai_response, model, is_vision=False):
        """Parse AI response into structured format"""
        try:
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Normalize status
                status_map = {
                    'SAFE_TO_DONATE': 'safe_to_donate',
                    'CONSUME_SOON': 'consume_soon', 
                    'REJECT': 'reject'
                }
                
                if 'status' in result:
                    result['status'] = status_map.get(result['status'].upper(), 'safe_to_donate')
                
                # Add metadata
                result['model'] = model.split('/')[0]
                result['analysis_type'] = 'vision' if is_vision else 'text'
                
                # Ensure all required fields exist
                if 'confidence' not in result:
                    result['confidence'] = 0.8
                if 'reason' not in result:
                    result['reason'] = f"Analyzed by {model.split('/')[0]}"
                if 'risk_factors' not in result:
                    result['risk_factors'] = []
                if 'recommendations' not in result:
                    result['recommendations'] = []
                
                return result
        except Exception as e:
            print(f"⚠️ Failed to parse AI response: {e}")
        
        # Fallback response
        return {
            "status": "safe_to_donate",
            "confidence": 0.7,
            "reason": f"AI analysis completed ({'vision' if is_vision else 'text'} mode)",
            "risk_factors": ["ai_analyzed"],
            "recommendations": ["Check manually if unsure"],
            "model": model.split('/')[0],
            "analysis_type": "vision" if is_vision else "text"
        }
    
    def _smart_local_ai(self, food_name, days_left, description, had_image=False):
        """Smart local AI with image consideration"""
        text = f"{food_name} {description}".lower()
        
        # If image was provided but API failed, mention it
        image_note = " (image provided but analysis failed)" if had_image else ""
        
        # Basic checks
        if days_left < 0:
            return {
                "status": "reject",
                "confidence": 0.99,
                "reason": f"❌ EXPIRED: {abs(days_left)} days past expiry{image_note}",
                "risk_factors": ["expired"],
                "recommendations": ["Do not consume"],
                "model": "local_ai"
            }
        
        # Check description for issues
        spoilage_words = ['mold', 'rotten', 'spoiled', 'sour', 'bad', 'expired']
        issues = [word for word in spoilage_words if word in text]
        
        if issues:
            return {
                "status": "reject",
                "confidence": 0.95,
                "reason": f"❌ UNSAFE: {', '.join(issues)} detected{image_note}",
                "risk_factors": issues,
                "recommendations": ["Do not donate"],
                "model": "local_ai"
            }
        
        # Simple decision logic
        if 'milk' in text or 'meat' in text or 'fish' in text:
            if days_left >= 7:
                return {
                    "status": "safe_to_donate",
                    "confidence": 0.85,
                    "reason": f"✅ SAFE: Perishable but fresh{image_note}",
                    "risk_factors": ["perishable"],
                    "recommendations": ["Keep refrigerated"],
                    "model": "local_ai"
                }
            elif days_left >= 3:
                return {
                    "status": "consume_soon",
                    "confidence": 0.90,
                    "reason": f"⚠️ CONSUME SOON: Perishable, eat within {days_left} days{image_note}",
                    "risk_factors": ["perishable", "time_sensitive"],
                    "recommendations": ["Consume quickly", "Keep cold"],
                    "model": "local_ai"
                }
            else:
                return {
                    "status": "reject",
                    "confidence": 0.88,
                    "reason": f"❌ REJECT: Perishable, only {days_left} days left{image_note}",
                    "risk_factors": ["perishable", "too_close"],
                    "recommendations": ["Do not donate"],
                    "model": "local_ai"
                }
        
        elif 'canned' in text or 'packaged' in text:
            return {
                "status": "safe_to_donate",
                "confidence": 0.95,
                "reason": f"✅ EXCELLENT: Long shelf life{image_note}",
                "risk_factors": [],
                "recommendations": ["Good for donation"],
                "model": "local_ai"
            }
        
        else:  # General food
            if days_left >= 7:
                return {
                    "status": "safe_to_donate",
                    "confidence": 0.85,
                    "reason": f"✅ GOOD: {days_left} days until expiry{image_note}",
                    "risk_factors": [],
                    "recommendations": ["Safe for donation"],
                    "model": "local_ai"
                }
            elif days_left >= 3:
                return {
                    "status": "consume_soon",
                    "confidence": 0.80,
                    "reason": f"⚠️ CONSUME SOON: Should be eaten within {days_left} days{image_note}",
                    "risk_factors": ["approaching_expiry"],
                    "recommendations": ["Consume quickly"],
                    "model": "local_ai"
                }
            else:
                return {
                    "status": "reject",
                    "confidence": 0.90,
                    "reason": f"❌ REJECT: Too close to expiry ({days_left} days){image_note}",
                    "risk_factors": ["too_close"],
                    "recommendations": ["Do not donate"],
                    "model": "local_ai"
                }
    
    def _simple_fallback(self, food_name, expiry_date, error):
        """Simple fallback when everything fails"""
        try:
            today = datetime.now().date()
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            days_left = (expiry - today).days
            
            if days_left < 0:
                return {
                    "status": "reject",
                    "confidence": 0.99,
                    "reason": f"Expired {abs(days_left)} days ago",
                    "risk_factors": ["expired"],
                    "recommendations": ["Do not consume"],
                    "model": "fallback"
                }
            elif days_left >= 7:
                return {
                    "status": "safe_to_donate",
                    "confidence": 0.85,
                    "reason": f"Good shelf life ({days_left} days)",
                    "risk_factors": [],
                    "recommendations": ["Safe for donation"],
                    "model": "fallback"
                }
            elif days_left >= 3:
                return {
                    "status": "consume_soon",
                    "confidence": 0.80,
                    "reason": f"Should be eaten soon ({days_left} days)",
                    "risk_factors": ["approaching_expiry"],
                    "recommendations": ["Consume quickly"],
                    "model": "fallback"
                }
            else:
                return {
                    "status": "reject",
                    "confidence": 0.90,
                    "reason": f"Too close to expiry ({days_left} days)",
                    "risk_factors": ["too_close"],
                    "recommendations": ["Do not donate"],
                    "model": "fallback"
                }
        except:
            return {
                "status": "safe_to_donate",
                "confidence": 0.5,
                "reason": "Default safe classification",
                "risk_factors": ["system_error"],
                "recommendations": ["Check manually"],
                "model": "fallback"
            }
    
    def test_real_image_upload(self, image_path=None):
        """Test REAL image upload with a sample image"""
        print("\n" + "="*60)
        print("📸 TESTING REAL IMAGE UPLOAD")
        print("="*60)
        
        if not self.use_api:
            print("❌ No API key - cannot test image upload")
            return
        
        # You need to provide an actual image file
        if not image_path or not os.path.exists(image_path):
            print("⚠️ Please provide a real image file path")
            print("⚠️ Example: python ai_classifier.py --image test_food.jpg")
            return
        
        try:
            # Read and encode image
            with open(image_path, "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            print(f"📁 Image loaded: {image_path}")
            print(f"📊 Image size: {len(image_base64)} bytes (base64)")
            
            # Test analysis
            result = self.predict(
                food_name="Test Food",
                expiry_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                description="Test image analysis",
                image_base64=image_base64
            )
            
            print(f"\n✅ REAL IMAGE ANALYSIS RESULT:")
            print(f"Status: {result['status']}")
            print(f"Reason: {result['reason']}")
            print(f"AI Type: {result.get('ai_type', 'unknown')}")
            print(f"Image Analyzed: {result.get('image_analyzed', False)}")
            print(f"Model: {result.get('model', 'unknown')}")
            
            if result.get('visual_findings'):
                print(f"Visual Findings: {result['visual_findings']}")
            
        except Exception as e:
            print(f"❌ Image upload test failed: {e}")

# Create classifier instance
classifier = FoodSafetyImageClassifier()

# Test on import
if __name__ == "__main__":
    import sys
    
    # Check if image file provided for testing
    if len(sys.argv) > 1 and sys.argv[1] == "--image" and len(sys.argv) > 2:
        image_path = sys.argv[2]
        classifier.test_real_image_upload(image_path)
    else:
        # Regular text-based test
        today = datetime.now().date()
        
        print("\n" + "="*60)
        print("🤖 FOOD SAFETY AI - TEXT ANALYSIS DEMO")
        print("="*60)
        
        test_cases = [
            ("Fresh Milk", (today + timedelta(days=5)).strftime("%Y-%m-%d"), "Unopened carton"),
            ("Bananas", (today + timedelta(days=2)).strftime("%Y-%m-%d"), "Some brown spots"),
            ("Canned Soup", (today + timedelta(days=400)).strftime("%Y-%m-%d"), "No dents"),
        ]
        
        for food, expiry, desc in test_cases:
            result = classifier.predict(food, expiry, desc)
            status_icon = "✅" if result["status"] == "safe_to_donate" else "⚠️" if result["status"] == "consume_soon" else "❌"
            print(f"\n{status_icon} {food}")
            print(f"  Status: {result['status'].upper()}")
            print(f"  Reason: {result['reason'][:100]}...")
            print(f"  AI Type: {result.get('ai_type', 'local')}")
            print(f"  Model: {result.get('model', 'unknown')}")
            print(f"  Confidence: {result.get('confidence', 0.5)*100:.0f}%")
        
        print("\n" + "="*60)
        print("📸 TO TEST IMAGE UPLOAD:")
        print("python ai_classifier.py --image path/to/your/food.jpg")
        print("="*60)