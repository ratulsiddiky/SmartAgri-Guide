from flask import Flask, jsonify, make_response
from flask_cors import CORS

from config import Config
from extensions import limiter


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["RATELIMIT_DEFAULT"] = Config.RATE_LIMIT_DEFAULTS
    CORS(app)

    limiter.init_app(app)

    # import blueprints (after app creation)
    from blueprints.auth.auth import auth_bp
    from blueprints.farms.farms import farms_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(farms_bp)

    @app.route("/", methods=["GET"])
    def home():
        return make_response(
            jsonify({"message": "Welcome to the Smart Agriculture API!"}), 200
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)