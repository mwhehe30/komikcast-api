from flask import Flask
from flask_cors import CORS
from routes.komikcast import komikcast
from flask import Response


def create_app():
    app = Flask(__name__)
    app.json.sort_keys = False
    app.url_map.strict_slashes = False
    CORS(app)
    app.register_blueprint(komikcast)

    @app.route("/")
    def index():
        return {
            "message": "Welcome to the API",
            "name": "Unofficial KomikCast API",
            "description": "API for scraping komikcast",
            "author": "Mwhehe30",
            "docs": "https://github.com/mwhehe30/komikcast-api",
            "version": "1.0.0",
        }

    @app.errorhandler(404)
    def not_found(error):
        return {
            "success": False,
            "error": "Not Found",
            "message": "Endpoint not found",
        }, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {
            "success": False,
            "error": "Internal Server Error",
            "message": "Internal server error",
        }, 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run()
