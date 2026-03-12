from flask import jsonify, request, make_response
import jwt
from functools import wraps
import globals

users = globals.db.users
blacklist = globals.db.blacklist

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Accept token from Authorization header or x-access-token
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        elif 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        if not token:
            return make_response(jsonify({'message': 'Token is missing! Please log in.'}), 401)
        
        try:
            data = jwt.decode(token, globals.SECRET_KEY, algorithms=["HS256"])
            current_user = users.find_one({"username": data['username']})
        except:
            return make_response(jsonify({'message': 'Token is invalid or expired!'}), 401)
        
        # NEW: Check if the user has logged out
        bl_token = blacklist.find_one({'token': token})
        if bl_token is not None:
            return make_response(jsonify({'message': 'Token has been cancelled/logged out'}), 401)
            
        return f(current_user, *args, **kwargs)
    return decorated