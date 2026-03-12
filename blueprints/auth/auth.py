from flask import Blueprint, request, jsonify, make_response
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
    if not data or not data.get('username') or not data.get('password'):
        return make_response(jsonify({'message': 'Username and password are required'}), 400)
    
    if users.find_one({'username': data['username']}):
        return make_response(jsonify({'message': 'Username is already taken'}), 409)
    
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), salt)
    
    new_user = {
        "username": data['username'],
        "password": hashed_password.decode('utf-8'),
        "role": data.get('role', 'user'),
        "contact_preference": data.get('contact_preference', 'email'),
        "created_at": datetime.datetime.utcnow()
    }
    users.insert_one(new_user)
    return make_response(jsonify({'message': f"Account created for {data['username']}!"}), 201)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({'message': 'Missing username or password'}), 401)
    
    user = users.find_one({'username': auth.username})
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)
    
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

# NEW: LOGOUT ROUTE
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