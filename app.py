from flask import Flask, jsonify, make_response
from flask_cors import CORS

from config import Config
from extensions import limiter


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["RATELIMIT_DEFAULT"] = "; ".join(Config.RATE_LIMIT_DEFAULTS)
    CORS(
        app,
        resources={
            r"/*": {
                "origins": ["http://localhost:4200"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    limiter.init_app(app)

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