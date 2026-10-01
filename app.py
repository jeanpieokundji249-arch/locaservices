import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'locaservices_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locaservices.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Configuration des numéros de réception Mobile Money (à personnaliser)
MOBILE_MONEY_NUMBERS = {
    'M-Pesa': '+243 81 000 0000',
    'Orange Money': '+243 89 000 0000',
    'Airtel Money': '+243 98 619 2491'
}

db = SQLAlchemy(app)

# --- Modèles ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_boosted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False) # 15%
    payment_status = db.Column(db.String(50), default='En attente de paiement')
    transaction_id = db.Column(db.String(100), nullable=True) # Code SMS Mobile Money
    payment_method = db.Column(db.String(50), nullable=True)

with app.app_context():
    db.create_all()

# --- Routes ---
@app.route('/')
def index():
    listings = Listing.query.order_by(Listing.is_boosted.desc(), Listing.id.desc()).all()
    return render_template('index.html', listings=listings)

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
        payment_method = request.form.get('payment_method')
        tx_id = request.form.get('transaction_id')
        
        booking.payment_method = payment_method
        booking.transaction_id = tx_id
        booking.payment_status = 'Paiement sous vérification'
        db.session.commit()
        
        flash("Votre référence de paiement a été soumise avec succès ! Validation sous peu.")
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
