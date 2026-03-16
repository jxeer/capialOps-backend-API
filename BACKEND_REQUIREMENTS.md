# CapitalOps Backend Requirements

**Last Updated:** 2026-03-16  
**Status:** Phase 4 Implementation Complete ✅

### Implementation Complete ✅

**Phase 4 - Profile Enhancement:**

1. **User Model Extended (20 new fields)**

2. **Connection System Added**

3. **S3 Upload Endpoint Created**

4. **API Endpoints Added**

5. **Environment Variables Updated**

---

This document outlines what needs to be added to the backend API to support Phase 4 features (Profile Enhancement) and future phases.

---

## Current State

### Implemented:
- ✅ Standard 10-core entities (Portfolio, Asset, Project, Deal, Investor, Allocation, Milestone, Vendor, WorkOrder, RiskFlag)
- ✅ Auth with JWT (flask-jwt-extended)
- ✅ /api/v1/ routes with JWT authentication
- ✅ /api/ compatibility layer (snake_case → camelCase, string IDs)

### Missing for Phase 4:
- Profile image upload (S3) ✅
- Profile type fields (investor/vendor/developer) ✅
- Connection system ✅
- Messaging system ✅

---

## Phase 4 - Profile Enhancement Requirements

### 1. User Model Extension

**Add to `app/models.py` (User class):**

```python
# Add to User model __init__ or as new columns:
profile_type = db.Column(db.String(20))  # "investor", "vendor", "developer"
profile_status = db.Column(db.String(20), default="pending")  # "pending", "active", "inactive", "suspended"
title = db.Column(db.String(100))
organization = db.Column(db.String(200))
linked_in_url = db.Column(db.String(500))
bio = db.Column(db.Text)

# Investor-specific
geographic_focus = db.Column(db.String(200))
investment_stage = db.Column(db.String(100))
target_return = db.Column(db.String(100))
check_size_min = db.Column(db.Numeric(15, 2))
check_size_max = db.Column(db.Numeric(15, 2))
risk_tolerance = db.Column(db.String(20))  # "Conservative", "Moderate", "Aggressive"
strategic_interest = db.Column(db.String(100))

# Vendor-specific
service_types = db.Column(db.String(200))
geographic_service_area = db.Column(db.String(200))
years_of_experience = db.Column(db.String(50))
certifications = db.Column(db.Text)
average_project_size = db.Column(db.Numeric(15, 2))

# Developer-specific
development_focus = db.Column(db.String(100))
development_type = db.Column(db.String(100))
team_size = db.Column(db.Integer)
portfolio_value = db.Column(db.Numeric(15, 2))
```

### 2. User Schema Update

**Update `User.to_dict()` method:**

```python
def to_dict(self):
    return {
        "id": str(self.id),
        "username": self.username,
        "email": self.email,
        "role": self.role,
        "role_display": self.role_display,
        "full_name": self.full_name,
        "profileType": self.profile_type,  # camelCase for frontend
        "profileStatus": self.profile_status,
        "title": self.title,
        "organization": self.organization,
        "linkedInUrl": self.linked_in_url,
        "bio": self.bio,
        "geographicFocus": self.geographic_focus,
        "investmentStage": self.investment_stage,
        "targetReturn": self.target_return,
        "checkSizeMin": float(self.check_size_min) if self.check_size_min else None,
        "checkSizeMax": float(self.check_size_max) if self.check_size_max else None,
        "riskTolerance": self.risk_tolerance,
        "strategicInterest": self.strategic_interest,
        "serviceTypes": self.service_types,
        "geographicServiceArea": self.geographic_service_area,
        "yearsOfExperience": self.years_of_experience,
        "certifications": self.certifications,
        "averageProjectSize": float(self.average_project_size) if self.average_project_size else None,
        "developmentFocus": self.development_focus,
        "developmentType": self.development_type,
        "teamSize": self.team_size,
        "portfolioValue": float(self.portfolio_value) if self.portfolio_value else None,
    }
```

### 3. Profile Image Upload Endpoint

**Add to `app/routes/compat.py`:**

```python
import boto3
from boto3.s3.transfer import TransferConfig

@compat_bp.route("/upload", methods=["POST"])
def upload():
    """
    Handle file uploads (images for profile avatars).
    
    Required headers:
        X-API-Key: <compat_api_key>
    
    Required form-data:
        file: <image file>
        path: "avatars/user-id/timestamp-filename.jpg"
        contentType: "image/jpeg"
        fileName: "original.jpg"
    
    Returns:
        {
            "url": "https://bucket.s3.amazonaws.com/avatars/...",
            "key": "avatars/user-id/timestamp-filename.jpg"
        }
    """
    api_key = os.environ.get("COMPAT_API_KEY")
    if api_key and request.headers.get("X-API-Key") != api_key:
        return jsonify({"error": "Invalid API key"}), 403
    
    file = request.files.get("file")
    path = request.form.get("path")
    if not file or not path:
        return jsonify({"error": "File and path required"}), 400
    
    # Upload to S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1")
    )
    
    bucket_name = os.environ.get("AWS_BUCKET_NAME")
    s3.upload_fileobj(file, bucket_name, path)
    
    url = f"https://{bucket_name}.s3.amazonaws.com/{path}"
    return jsonify({"url": url, "key": path})
```

**Required Environment Variables:**
```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_BUCKET_NAME=
COMPAT_API_KEY=  # must match frontend's COMPAT_API_KEY
```

### 4. Connection & Messaging Endpoints

**Add to `app/routes/compat.py` (and new models.py models):**

```python
# New models (add to models.py):
class ConnectionRequest(db.Model):
    __tablename__ = "connection_requests"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # "pending", "accepted", "declined"
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    sender = db.relationship("User", foreign_keys=[sender_id])

class Conversation(db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)
    user_id1 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_id2 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship("User", foreign_keys=[sender_id])
    conversation = db.relationship("Conversation", backref="messages")
```

**API Endpoints to add:**
- `GET /api/connection-requests` - List connection requests for current user
- `POST /api/connection-requests` - Send connection request
- `PUT /api/connection-requests/:id` - Accept/decline request
- `DELETE /api/connection-requests/:id` - Withdraw request
- `GET /api/connections` - Get connected users
- `GET /api/connection-pending` - Get pending incoming requests
- `GET /api/conversations` - List conversations for current user
- `POST /api/conversations` - Create conversation with user
- `GET /api/messages?conversationId=:id` - Get messages in conversation
- `POST /api/messages` - Send message
- `PUT /api/messages/:id/read` - Mark message as read
- `DELETE /api/messages/:id` - Delete message

### 5. Profile Update Endpoint

**Update existing route to support new fields:**

The `PUT /api/users/:id` route in `compat.py` should already work since it passes the full request body to the database. Ensure the schema validation allows all new fields.

---

## Backend Development Checklist

### Priority 1 (Phase 4 Core):
- [X] Extend User model with new profile fields (profile_type, profile_status, etc.) ✅
- [X] Add ConnectionRequest, Conversation, Message models ✅
- [X] Create `/upload` endpoint for S3 file uploads ✅
- [X] Create connection/messaging API endpoints ✅
- [X] Update User.to_dict() to include new fields ✅
- [X] Add environment variable configuration for AWS S3 ✅

### Priority 2 (Testing):
- [ ] Test profile image upload
- [ ] Test connection request send/accept/decline flow
- [ ] Test messaging between connected users
- [ ] Verify camelCase field names in responses

### Priority 3 (Documentation):
- [ ] Update API documentation with new endpoints
- [ ] Update seed data to include example profile data
- [ ] Add tests for new functionality

---

## Notes

- Backend already has `compat.py` for GUI compatibility (snake_case to camelCase, string IDs)
- Use the existing `compat_bp` blueprint for all new routes
- All routes are prefixed with `/api/` automatically by the app factory
- API key authentication via `X-API-Key` header for mutations
