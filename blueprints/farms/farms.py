from datetime import datetime

import requests
from bson import ObjectId
from flask import Blueprint, jsonify, make_response, request

from blueprints.farms.models import (
    validate_alert_payload,
    validate_farm_payload,
    validate_sensor_payload,
)
from config import get_db
from decorators import jwt_required
from utils.validators import serialize_document

farms_bp = Blueprint("farms_bp", __name__)


def _farms_collection():
    return get_db().farms


def get_farm_if_authorised(farm_id, current_user):
    if not ObjectId.is_valid(farm_id):
        return None, make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    farm = _farms_collection().find_one({"_id": ObjectId(farm_id)})
    if not farm:
        return None, make_response(jsonify({"message": "Farm not found"}), 404)

    if current_user.get("role") == "admin":
        return farm, None

    if str(farm["owner_id"]) != str(current_user["_id"]):
        return None, make_response(
            jsonify({"message": "Access denied. You can only manage your own farms."}),
            403,
        )

    return farm, None


@farms_bp.route("/api/farms", methods=["GET"])
def get_all_farms():
    farms_list = [serialize_document(farm) for farm in _farms_collection().find({})]
    return make_response(jsonify(farms_list), 200)


@farms_bp.route("/api/farms/<farm_id>", methods=["GET"])
def get_single_farm(farm_id):
    if not ObjectId.is_valid(farm_id):
        return make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    farm = _farms_collection().find_one({"_id": ObjectId(farm_id)})
    if not farm:
        return make_response(jsonify({"message": "Farm not found"}), 404)

    return make_response(jsonify(serialize_document(farm)), 200)


@farms_bp.route("/api/farms", methods=["POST"])
@jwt_required
def create_farm(current_user):
    farm_data, error = validate_farm_payload(request.get_json(silent=True))
    if error:
        return make_response(jsonify({"message": error}), 400)

    farm_data["owner_id"] = current_user["_id"]
    farm_data["created_at"] = datetime.utcnow()
    result = _farms_collection().insert_one(farm_data)

    return make_response(
        jsonify({"message": "Farm registered successfully!", "farm_id": str(result.inserted_id)}),
        201,
    )


@farms_bp.route("/api/farms/<farm_id>", methods=["PUT"])
@jwt_required
def update_farm(current_user, farm_id):
    _, error_response = get_farm_if_authorised(farm_id, current_user)
    if error_response:
        return error_response

    updates, error = validate_farm_payload(request.get_json(silent=True), partial=True)
    if error:
        return make_response(jsonify({"message": error}), 400)

    _farms_collection().update_one({"_id": ObjectId(farm_id)}, {"$set": updates})
    return make_response(jsonify({"message": "Farm updated successfully!"}), 200)


@farms_bp.route("/api/farms/<farm_id>", methods=["DELETE"])
@jwt_required
def delete_farm(current_user, farm_id):
    if current_user.get("role") != "admin":
        return make_response(jsonify({"message": "Admin access required"}), 403)

    if not ObjectId.is_valid(farm_id):
        return make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    result = _farms_collection().delete_one({"_id": ObjectId(farm_id)})
    if result.deleted_count == 0:
        return make_response(jsonify({"message": "Farm not found"}), 404)

    return make_response(jsonify({"message": "Farm deleted successfully"}), 200)


@farms_bp.route("/api/farms/<farm_id>/sensors", methods=["POST"])
@jwt_required
def add_sensor(current_user, farm_id):
    _, error_response = get_farm_if_authorised(farm_id, current_user)
    if error_response:
        return error_response

    sensor, error = validate_sensor_payload(request.get_json(silent=True))
    if error:
        return make_response(jsonify({"message": error}), 400)

    _farms_collection().update_one({"_id": ObjectId(farm_id)}, {"$push": {"sensors": sensor}})
    return make_response(jsonify({"message": "Sensor added to farm!", "sensor": sensor}), 201)


@farms_bp.route("/api/farms/search", methods=["GET"])
def search_farms():
    search_term = request.args.get("q", "").strip()
    if not search_term:
        return make_response(jsonify({"message": "Provide search term using ?q="}), 400)

    search_results = _farms_collection().find({"$text": {"$search": search_term}})
    farms_list = [serialize_document(farm) for farm in search_results]
    return make_response(jsonify({"results_count": len(farms_list), "data": farms_list}), 200)


@farms_bp.route("/api/farms/<farm_id>/sync_weather", methods=["POST"])
@jwt_required
def sync_weather(current_user, farm_id):
    farm, error_response = get_farm_if_authorised(farm_id, current_user)
    if error_response:
        return error_response

    coordinates = farm.get("location", {}).get("coordinates", [])
    if len(coordinates) != 2:
        return make_response(jsonify({"message": "Farm location is incomplete."}), 400)

    lng, lat = coordinates
    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}&current_weather=true"
    )

    try:
        response = requests.get(weather_url, timeout=10)
        response.raise_for_status()
        weather_data = response.json()
    except requests.RequestException as exc:
        return make_response(jsonify({"message": "API error", "error": str(exc)}), 502)

    current_weather = weather_data.get("current_weather", {})
    new_log = {
        "timestamp": datetime.utcnow(),
        "temperature_celsius": current_weather.get("temperature"),
        "windspeed": current_weather.get("windspeed"),
        "conditions": "Synced from Open-Meteo API",
    }

    _farms_collection().update_one({"_id": ObjectId(farm_id)}, {"$push": {"weather_logs": new_log}})
    return make_response(jsonify({"message": "Weather synced!", "new_log": new_log}), 200)


@farms_bp.route("/api/farms/alerts/broadcast", methods=["POST"])
@jwt_required
def broadcast_alert(current_user):
    if current_user.get("role") != "admin":
        return make_response(jsonify({"message": "Admin access required"}), 403)

    data, error = validate_alert_payload(request.get_json(silent=True))
    if error:
        return make_response(jsonify({"message": error}), 400)

    geo_query = {"location": {"$geoWithin": {"$geometry": data["danger_zone"]}}}
    affected_farms = list(_farms_collection().find(geo_query))
    alert_entry = {
        "alert_type": data["alert_type"],
        "timestamp": datetime.utcnow(),
        "message": f"EMERGENCY: {data['alert_type']} warning issued!",
        "issued_by": current_user.get("username", "admin"),
    }

    _farms_collection().update_many(geo_query, {"$push": {"alerts_history": alert_entry}})
    return make_response(jsonify({"message": "Alert broadcast!", "farms_notified": len(affected_farms)}), 200)


@farms_bp.route("/api/farms/<farm_id>/insights", methods=["GET"])
@jwt_required
def get_farm_insights(current_user, farm_id):
    _, error_response = get_farm_if_authorised(farm_id, current_user)
    if error_response:
        return error_response

    pipeline = [
        {"$match": {"_id": ObjectId(farm_id)}},
        {"$unwind": "$weather_logs"},
        {
            "$group": {
                "_id": "$_id",
                "farm_name": {"$first": "$farm_name"},
                "average_temp": {"$avg": "$weather_logs.temperature_celsius"},
                "average_wind": {"$avg": "$weather_logs.windspeed"},
            }
        },
    ]

    try:
        result = list(_farms_collection().aggregate(pipeline))
    except Exception as exc:
        return make_response(jsonify({"message": "Error", "error": str(exc)}), 500)

    if not result:
        return make_response(jsonify({"message": "Not enough data"}), 404)

    insights = serialize_document(result[0])
    if insights.get("average_temp") is not None:
        insights["average_temp"] = round(insights["average_temp"], 2)
    if insights.get("average_wind") is not None:
        insights["average_wind"] = round(insights["average_wind"], 2)

    return make_response(jsonify({"message": "Insights generated", "dashboard_data": insights}), 200)


@farms_bp.route("/api/farms/<farm_id>/irrigation_check", methods=["GET"])
@jwt_required
def check_irrigation(current_user, farm_id):
    farm, error_response = get_farm_if_authorised(farm_id, current_user)
    if error_response:
        return error_response

    try:
        moisture_level = None
        for sensor in farm.get("sensors", []):
            if sensor.get("type") == "Soil Moisture":
                readings = sensor.get("readings", [])
                if readings:
                    moisture_level = readings[-1]["value"]
                break

        if moisture_level is None:
            return make_response(jsonify({"message": "No soil moisture sensor found."}), 404)

        status = "WARNING" if moisture_level < 20.0 else "OK"
        return make_response(jsonify({"status": status, "moisture": moisture_level}), 200)
    except Exception as exc:
        return make_response(jsonify({"message": "Error", "error": str(exc)}), 500)


@farms_bp.route("/api/farms/region/<region_name>/insights", methods=["GET"])
def get_regional_insights(region_name):
    pipeline = [
        {"$match": {"address.area_name": region_name}},
        {"$unwind": "$weather_logs"},
        {
            "$group": {
                "_id": region_name,
                "community_avg_temp": {"$avg": "$weather_logs.temperature_celsius"},
                "unique_farms": {"$addToSet": "$_id"},
            }
        },
        {
            "$project": {
                "community_avg_temp": {"$round": ["$community_avg_temp", 2]},
                "total_farms_included": {"$size": "$unique_farms"},
            }
        },
    ]

    try:
        result = list(_farms_collection().aggregate(pipeline))
    except Exception as exc:
        return make_response(jsonify({"message": "Error", "error": str(exc)}), 500)

    if not result:
        return make_response(jsonify({"message": "No data found."}), 404)

    return make_response(jsonify({"message": "Community averages", "data": serialize_document(result[0])}), 200)
