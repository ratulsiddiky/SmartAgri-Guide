from flask import Blueprint, request, jsonify, make_response
from bson.objectid import ObjectId
import bcrypt
import jwt
import datetime
import globals
from decorators import jwt_required

auth_bp = Blueprint('auth_bp', __name__)

users = globals.db.users
blacklist = globals.db.blacklist

@auth_bp.route('/api/users/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # REQUIRE EMAIL NOW
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return make_response(jsonify({'message': 'Username, email, and password are required'}), 400)
    
    # Check if username OR email is already taken
    if users.find_one({'$or': [{'username': data['username']}, {'email': data['email']}]}):
        return make_response(jsonify({'message': 'Username or Email is already registered'}), 409)
    
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), salt)
    
    new_user = {
        "username": data['username'],
        "email": data['email'],
        "password": hashed_password.decode('utf-8'),
        "role": data.get('role', 'user'),
        "contact_preference": data.get('contact_preference', 'email'),
        "is_verified": False, # <-- NEW: Unverified by default!
        "created_at": datetime.datetime.utcnow()
    }
    result = users.insert_one(new_user)
    
    # SIMULATE SENDING AN EMAIL
    verification_link = f"http://127.0.0.1:5001/api/users/verify/{str(result.inserted_id)}"
    
    return make_response(jsonify({
        'message': f"Account created for {data['username']}! Please verify your email.",
        'verification_link': verification_link # In the real world, this is sent to their inbox
    }), 201)

# NEW: VERIFY EMAIL ROUTE
@auth_bp.route('/api/users/verify/<user_id>', methods=['GET'])
def verify_email(user_id):
    try:
        result = users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_verified": True}}
        )
        if result.matched_count == 0:
            return make_response(jsonify({"message": "User not found"}), 404)
        
        return make_response(jsonify({"message": "Email successfully verified! You can now log in."}), 200)
    except:
        return make_response(jsonify({"message": "Invalid verification link"}), 400)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({'message': 'Missing username or password'}), 401)
    
    user = users.find_one({'username': auth.username})
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)
        
    # <-- NEW: BLOCK LOGIN IF NOT VERIFIED
    if not user.get('is_verified', False):
        return make_response(jsonify({'message': 'Please verify your email before logging in.'}), 403)
    
    if bcrypt.checkpw(auth.password.encode('utf-8'), user['password'].encode('utf-8')):
        token = jwt.encode(
            {
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            },
            globals.SECRET_KEY,
            algorithm="HS256"
        )
        return make_response(jsonify({
            'message': 'Login successful!',
            'token': token,
            'username': user['username'],
            'role': user['role']
        }), 200)
    
    return make_response(jsonify({'message': 'Incorrect password'}), 401)

@auth_bp.route('/api/logout', methods=['GET'])
@jwt_required
def logout(current_user):
    token = None
    if 'Authorization' in request.headers:
        token = request.headers['Authorization'].split(" ")[1]
    elif 'x-access-token' in request.headers:
        token = request.headers['x-access-token']
        
    blacklist.insert_one({'token': token})
    return make_response(jsonify({'message': 'Logout successful'}), 200)

@auth_bp.route('/api/users', methods=['GET'])
@jwt_required
def get_all_users(current_user):
    if current_user.get('role') != 'admin':
        return make_response(jsonify({'message': 'Admin access required'}), 403)
    
    users_cursor = users.find({}, {"password": 0})
    users_list = []
    for user in users_cursor:
        user['_id'] = str(user['_id'])
        users_list.append(user)
        
    return make_response(jsonify({"count": len(users_list), "users": users_list}), 200)