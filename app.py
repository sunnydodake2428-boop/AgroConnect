from flask import Flask, render_template
from extensions import db, bcrypt
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)

    from routes.auth import auth
    from routes.farmer import farmer
    from routes.buyer import buyer
    from routes.admin import admin
    from routes.ml import ml

    app.register_blueprint(auth)
    app.register_blueprint(farmer)
    app.register_blueprint(buyer)
    app.register_blueprint(admin)
    app.register_blueprint(ml)

    @app.route('/')
    def home():
        from models import Product
        featured_crops = Product.query.filter_by(status='available').limit(8).all()
        return render_template('home.html', featured_crops=featured_crops)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
    # Add this route to app.py

@app.route('/language-select')
def language_select():
    """Show language selection splash page."""
    return render_template('lang_splash.html')