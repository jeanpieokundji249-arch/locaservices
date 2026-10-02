import os
from datetime import datetime, timedelta
import urllib.parse
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'locaservices_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locaservices.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Informations de contact par défaut
DEFAULT_WHATSAPP = "243986192491"
DEFAULT_EMAIL = "jeanpieokundji249@gmail.com"
DEFAULT_FACEBOOK_PAGE = "Jean.pie.lange.okundji"

MOBILE_MONEY_NUMBERS = {
    'M-Pesa': '+243 81 000 0000',
    'Orange Money': '+243 89 000 0000',
    'Airtel Money': '+243 98 6192 491'
}

db = SQLAlchemy(app)

# --- Modèles ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_boosted = db.Column(db.Boolean, default=False)
    boosted_until = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), default='En attente')
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)

# Mise à jour automatique de la base de données sans perte de données
with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    
    # Vérifier et ajouter les nouvelles colonnes si elles manquent
    if 'listing' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('listing')]
        if 'boosted_until' not in columns:
            db.session.execute(text('ALTER TABLE listing ADD COLUMN boosted_until DATETIME'))
            db.session.commit()
            
    if 'user' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('user')]
        if 'phone' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN phone VARCHAR(20)'))
            db.session.commit()

# --- Générateur de liens de contact ---
def generate_contact_links(listing_title, phone=None, email=None, fb_page=None):
    clean_phone = phone.replace('+', '').replace(' ', '') if phone else DEFAULT_WHATSAPP
    target_email = email if email else DEFAULT_EMAIL
    target_fb = fb_page if fb_page else DEFAULT_FACEBOOK_PAGE

    msg = f"Bonjour, je suis intéressé(e) par l'annonce '{listing_title}' sur LocaServices."
    encoded_msg = urllib.parse.quote(msg)

    return {
        'whatsapp': f"https://wa.me/{clean_phone}?text={encoded_msg}",
        'email': f"mailto:{target_email}?subject={urllib.parse.quote('Demande sur LocaServices: ' + listing_title)}&body={encoded_msg}",
        'messenger': f"https://m.me/{target_fb}"
    }

@app.context_processor
def utility_processor():
    return dict(generate_contact_links=generate_contact_links)

# --- Routes ---
@app.route('/')
def index():
    now = datetime.utcnow()
    listings = Listing.query.all()
    
    # Desactiver les boosts expirés
    for listing in listings:
        if listing.is_boosted and listing.boosted_until and listing.boosted_until < now:
            listing.is_boosted = False
            db.session.commit()

    active_listings = Listing.query.order_by(Listing.is_boosted.desc(), Listing.id.desc()).all()
    return render_template('index.html', listings=active_listings)

@app.route('/reserve/<int:listing_id>', methods=['POST'])
def reserve(listing_id):
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour réserver.")
        return redirect(url_for('index'))
    
    listing = Listing.query.get_or_404(listing_id)
    commission = listing.price * 0.15
    
    new_booking = Booking(
        listing_id=listing.id,
        client_id=session['user_id'],
        total_price=listing.price,
        commission=commission,
        payment_status='En attente'
    )
    db.session.add(new_booking)
    db.session.commit()
    
    return redirect(url_for('pay_booking', booking_id=new_booking.id))

@app.route('/pay/<int:booking_id>', methods=['GET', 'POST'])
def pay_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        booking.payment_method = request.form.get('payment_method')
        booking.transaction_id = request.form.get('transaction_id')
        booking.payment_status = 'Paiement sous vérification'
        db.session.commit()
        
        flash("Référence enregistrée. Validation en cours.")
        return redirect(url_for('dashboard'))
        
    return render_template('pay.html', booking=booking, numbers=MOBILE_MONEY_NUMBERS)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user_bookings = Booking.query.filter_by(client_id=session['user_id']).all()
    return render_template('dashboard.html', bookings=user_bookings)

if __name__ == '__main__':
    app.run(debug=True)
