import datetime

import bcrypt
import jwt
from bson import ObjectId
from flask import Blueprint, jsonify, make_response, request

from blueprints.auth.models import validate_signup_payload
from config import Config, get_db
from decorators import jwt_required
from utils.validators import serialize_document

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/api/users/signup", methods=["POST"])
@auth_bp.route("/api/users/register", methods=["POST"])
def signup():
    payload, error = validate_signup_payload(request.get_json(silent=True))
    if error:
        return make_response(jsonify({"message": error}), 400)

    users = get_db().users
    if users.find_one(
        {"$or": [{"username": payload["username"]}, {"email": payload["email"]}]}
    ):
        return make_response(
            jsonify({"message": "Username or email is already registered."}),
            409,
        )

    hashed_password = bcrypt.hashpw(
        payload["password"].encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    result = users.insert_one(
        {
            "username": payload["username"],
            "email": payload["email"],
            "password": hashed_password,
            "role": payload["role"],
            "contact_preference": payload["contact_preference"],
            "is_verified": False,
            "created_at": datetime.datetime.utcnow(),
        }
    )
    verification_link = (
        f"http://{Config.HOST}:{Config.PORT}/api/users/verify/{result.inserted_id}"
    )

    return make_response(
        jsonify(
            {
                "message": f"Account created for {payload['username']}! Please verify your email.",
                "verification_link": verification_link,
            }
        ),
        201,
    )


@auth_bp.route("/api/users/verify/<user_id>", methods=["GET"])
def verify_email(user_id):
    users = get_db().users
    if not ObjectId.is_valid(user_id):
        return make_response(jsonify({"message": "Invalid verification link"}), 400)

    result = users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_verified": True}})
    if result.matched_count == 0:
        return make_response(jsonify({"message": "User not found"}), 404)

    return make_response(
        jsonify({"message": "Email successfully verified! You can now log in."}),
        200,
    )


@auth_bp.route("/api/login", methods=["POST"])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Missing username or password"}), 401)

    user = get_db().users.find_one({"username": auth.username})
    if not user:
        return make_response(jsonify({"message": "User not found"}), 404)

    if not user.get("is_verified", False):
        return make_response(
            jsonify({"message": "Please verify your email before logging in."}),
            403,
        )

    if not bcrypt.checkpw(
        auth.password.encode("utf-8"),
        user["password"].encode("utf-8"),
    ):
        return make_response(jsonify({"message": "Incorrect password"}), 401)

    token = jwt.encode(
        {
            "username": user["username"],
            "role": user["role"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
        },
        Config.SECRET_KEY,
        algorithm="HS256",
    )

    return make_response(
        jsonify(
            {
                "message": "Login successful!",
                "token": token,
                "username": user["username"],
                "role": user["role"],
            }
        ),
        200,
    )


@auth_bp.route("/api/logout", methods=["GET"])
@jwt_required
def logout(current_user):
    authorization = request.headers.get("Authorization", "").split()
    token = (
        authorization[1]
        if len(authorization) == 2 and authorization[0].lower() == "bearer"
        else request.headers.get("x-access-token")
    )
    get_db().blacklist.insert_one({"token": token, "username": current_user["username"]})
    return make_response(jsonify({"message": "Logout successful"}), 200)


@auth_bp.route("/api/users", methods=["GET"])
@jwt_required
def get_all_users(current_user):
    if current_user.get("role") != "admin":
        return make_response(jsonify({"message": "Admin access required"}), 403)

    users_list = [
        serialize_document(user)
        for user in get_db().users.find({}, {"password": 0})
    ]
    return make_response(jsonify({"count": len(users_list), "users": users_list}), 200)
