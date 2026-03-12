from flask import Flask, jsonify, make_response
from flask_cors import CORS

# Import your blueprints
from blueprints.auth.auth import auth_bp
from blueprints.farms.farms import farms_bp

app = Flask(__name__)
CORS(app) # This allows your Angular frontend to talk to this API later!

# Register our blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(farms_bp)

@app.route('/', methods=['GET'])
def home():
    return make_response(jsonify({"message": "Welcome to the Smart Agriculture API!"}), 200)

if __name__ == '__main__':
    app.run(debug=True, port=5001)