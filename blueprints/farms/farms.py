from flask import Blueprint, jsonify, request, make_response
import requests
from datetime import datetime
from bson.objectid import ObjectId

import globals
from decorators import jwt_required

farms_bp = Blueprint('farms_bp', __name__)
farms = globals.db.farms

# Helper Function
def get_farm_if_authorised(farm_id, current_user):
    try:
        oid = ObjectId(farm_id)
    except:
        return None, make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    farm = farms.find_one({"_id": oid})
    if not farm:
        return None, make_response(jsonify({"message": "Farm not found"}), 404)

    if current_user.get('role') == 'admin':
        return farm, None

    if str(farm['owner_id']) != str(current_user['_id']):
        return None, make_response(jsonify({"message": "Access denied. You can only manage your own farms."}), 403)

    return farm, None

@farms_bp.route('/api/farms', methods=['GET'])
def get_all_farms():
    farms_cursor = farms.find({})
    farms_list = []
    for farm in farms_cursor:
        farm['_id'] = str(farm['_id'])
        farm['owner_id'] = str(farm['owner_id'])
        farms_list.append(farm)
    return make_response(jsonify(farms_list), 200)

@farms_bp.route('/api/farms/<farm_id>', methods=['GET'])
def get_single_farm(farm_id):
    try:
        farm = farms.find_one({"_id": ObjectId(farm_id)})
    except:
        return make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    if not farm:
        return make_response(jsonify({"message": "Farm not found"}), 404)

    farm['_id'] = str(farm['_id'])
    farm['owner_id'] = str(farm['owner_id'])
    return make_response(jsonify(farm), 200)

@farms_bp.route('/api/farms', methods=['POST'])
@jwt_required
def create_farm(current_user):
    data = request.get_json()
    if not data or not data.get('farm_name'):
        return make_response(jsonify({"message": "Please provide at least a farm_name"}), 400)

    data['owner_id'] = current_user['_id']
    data.setdefault('sensors', [])
    data.setdefault('weather_logs', [])
    data.setdefault('alerts_history', [])
    data['created_at'] = datetime.now()

    result = farms.insert_one(data)
    return make_response(jsonify({"message": "Farm registered successfully!", "farm_id": str(result.inserted_id)}), 201)

@farms_bp.route('/api/farms/<farm_id>', methods=['PUT'])
@jwt_required
def update_farm(current_user, farm_id):
    farm, err = get_farm_if_authorised(farm_id, current_user)
    if err: return err

    data = request.get_json()
    if not data:
        return make_response(jsonify({"message": "No update data provided"}), 400)

    allowed_fields = ['farm_name', 'crop_type', 'address', 'location']
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return make_response(jsonify({"message": f"No valid fields provided."}), 400)

    farms.update_one({"_id": ObjectId(farm_id)}, {"$set": updates})
    return make_response(jsonify({"message": "Farm updated successfully!"}), 200)

@farms_bp.route('/api/farms/<farm_id>', methods=['DELETE'])
@jwt_required
def delete_farm(current_user, farm_id):
    if current_user.get('role') != 'admin':
        return make_response(jsonify({"message": "Admin access required"}), 403)

    try:
        result = farms.delete_one({"_id": ObjectId(farm_id)})
    except:
        return make_response(jsonify({"message": "Invalid farm ID format"}), 400)

    if result.deleted_count == 0:
        return make_response(jsonify({"message": "Farm not found"}), 404)

    return make_response(jsonify({"message": "Farm deleted successfully"}), 200)

@farms_bp.route('/api/farms/<farm_id>/sensors', methods=['POST'])
@jwt_required
def add_sensor(current_user, farm_id):
    farm, err = get_farm_if_authorised(farm_id, current_user)
    if err: return err

    data = request.get_json()
    if not data or not data.get('sensor_id') or not data.get('type'):
        return make_response(jsonify({"message": "sensor_id and type required"}), 400)

    new_sensor = {
        "sensor_id": data['sensor_id'],
        "type": data['type'],
        "status": data.get('status', True),
        "readings": data.get('readings', [])
    }

    farms.update_one({"_id": ObjectId(farm_id)}, {"$push": {"sensors": new_sensor}})
    return make_response(jsonify({"message": "Sensor added to farm!", "sensor": new_sensor}), 201)

@farms_bp.route('/api/farms/search', methods=['GET'])
def search_farms():
    search_term = request.args.get('q')
    if not search_term:
        return make_response(jsonify({"message": "Provide search term using ?q="}), 400)

    search_results = farms.find({"$text": {"$search": search_term}})
    farms_list = []
    for farm in search_results:
        farm['_id'] = str(farm['_id'])
        farm['owner_id'] = str(farm['owner_id'])
        farms_list.append(farm)

    return make_response(jsonify({"results_count": len(farms_list), "data": farms_list}), 200)

@farms_bp.route('/api/farms/<farm_id>/sync_weather', methods=['POST'])
@jwt_required
def sync_weather(current_user, farm_id):
    farm, err = get_farm_if_authorised(farm_id, current_user)
    if err: return err

    lng = farm['location']['coordinates'][0]
    lat = farm['location']['coordinates'][1]
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"

    try:
        response = requests.get(weather_url)
        weather_data = response.json()
        current_weather = weather_data.get('current_weather', {})

        new_log = {
            "timestamp": datetime.now(),
            "temperature_celsius": current_weather.get('temperature'),
            "windspeed": current_weather.get('windspeed'),
            "conditions": "Synced from Open-Meteo API"
        }

        farms.update_one({"_id": ObjectId(farm_id)}, {"$push": {"weather_logs": new_log}})
        return make_response(jsonify({"message": "Weather synced!", "new_log": new_log}), 200)

    except Exception as e:
        return make_response(jsonify({"message": "API error", "error": str(e)}), 500)

@farms_bp.route('/api/farms/alerts/broadcast', methods=['POST'])
@jwt_required
def broadcast_alert(current_user):
    if current_user.get('role') != 'admin':
        return make_response(jsonify({"message": "Admin access required"}), 403)

    data = request.get_json()
    if not data or 'alert_type' not in data or 'danger_zone' not in data:
        return make_response(jsonify({"message": "alert_type and danger_zone required"}), 400)

    geo_query = {"location": {"$geoWithin": {"$geometry": data['danger_zone']}}}
    affected_farms = list(farms.find(geo_query))

    alert_entry = {
        "alert_type": data['alert_type'],
        "timestamp": datetime.now(),
        "message": f"EMERGENCY: {data['alert_type']} warning issued!",
        "issued_by": current_user.get('username', 'admin')
    }

    farms.update_many(geo_query, {"$push": {"alerts_history": alert_entry}})
    return make_response(jsonify({"message": "Alert broadcast!", "farms_notified": len(affected_farms)}), 200)

@farms_bp.route('/api/farms/<farm_id>/insights', methods=['GET'])
@jwt_required
def get_farm_insights(current_user, farm_id):
    farm, err = get_farm_if_authorised(farm_id, current_user)
    if err: return err

    try:
        pipeline = [
            {"$match": {"_id": ObjectId(farm_id)}},
            {"$unwind": "$weather_logs"},
            {"$group": {
                "_id": "$_id",
                "farm_name": {"$first": "$farm_name"},
                "average_temp": {"$avg": "$weather_logs.temperature_celsius"},
                "average_wind": {"$avg": "$weather_logs.windspeed"}
            }}
        ]
        result = list(farms.aggregate(pipeline))

        if not result:
            return make_response(jsonify({"message": "Not enough data"}), 404)

        insights = result[0]
        insights['_id'] = str(insights['_id'])
        if insights.get('average_temp'): insights['average_temp'] = round(insights['average_temp'], 2)
        if insights.get('average_wind'): insights['average_wind'] = round(insights['average_wind'], 2)

        return make_response(jsonify({"message": "Insights generated", "dashboard_data": insights}), 200)

    except Exception as e:
        return make_response(jsonify({"message": "Error", "error": str(e)}), 500)

@farms_bp.route('/api/farms/<farm_id>/irrigation_check', methods=['GET'])
@jwt_required
def check_irrigation(current_user, farm_id):
    farm, err = get_farm_if_authorised(farm_id, current_user)
    if err: return err

    try:
        moisture_level = None
        for sensor in farm.get('sensors', []):
            if sensor.get('type') == 'Soil Moisture':
                readings = sensor.get('readings', [])
                if readings:
                    moisture_level = readings[-1]['value']
                break

        if moisture_level is None:
            return make_response(jsonify({"message": "No soil moisture sensor found."}), 404)

        if moisture_level < 20.0:
            return make_response(jsonify({"status": "WARNING", "moisture": moisture_level}), 200)
        else:
            return make_response(jsonify({"status": "OK", "moisture": moisture_level}), 200)

    except Exception as e:
        return make_response(jsonify({"message": "Error", "error": str(e)}), 500)

@farms_bp.route('/api/farms/region/<region_name>/insights', methods=['GET'])
def get_regional_insights(region_name):
    try:
        pipeline = [
            {"$match": {"address.area_name": region_name}},
            {"$unwind": "$weather_logs"},
            {"$group": {
                "_id": region_name,
                "community_avg_temp": {"$avg": "$weather_logs.temperature_celsius"},
                "unique_farms": {"$addToSet": "$_id"}
            }},
            {"$project": {
                "community_avg_temp": {"$round": ["$community_avg_temp", 2]},
                "total_farms_included": {"$size": "$unique_farms"}
            }}
        ]
        result = list(farms.aggregate(pipeline))

        if not result:
            return make_response(jsonify({"message": "No data found."}), 404)

        return make_response(jsonify({"message": f"Community averages", "data": result[0]}), 200)

    except Exception as e:
        return make_response(jsonify({"message": "Error", "error": str(e)}), 500)