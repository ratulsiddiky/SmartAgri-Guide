from flask import Flask, jsonify, make_response
from flask_cors import CORS

from blueprints import register_blueprints
from config import Config


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    CORS(app)
    register_blueprints(app)

    @app.route("/", methods=["GET"])
    def home():
        return make_response(
            jsonify({"message": "Welcome to the Smart Agriculture API!"}),
            200,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
