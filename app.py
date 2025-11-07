from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from urllib.parse import urlparse, unquote
import pymysql
from sqlalchemy import text
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'
db_url = os.environ.get('DATABASE_URL', 'sqlite:///movie_rental.db')

# Ensure MySQL database exists if using MySQL
if db_url.startswith('mysql'):  
    parsed = urlparse(db_url)
    db_name = unquote(parsed.path.lstrip('/'))
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 3306
    user = unquote(parsed.username or '')
    password = unquote(parsed.password or '')
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password)
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
        conn.close()
    except Exception as e:
        print(f"[WARN] Could not ensure MySQL database exists: {e}")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,
}
app.config['READ_API_TOKEN'] = os.environ.get('READ_API_TOKEN', '')

db = SQLAlchemy(app)

# Logging configuration (Rotating file + console)
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger('movie_rental')
logger.setLevel(getattr(logging, log_level, logging.INFO))
if not logger.handlers:
    fh = RotatingFileHandler('app.log', maxBytes=1_000_000, backupCount=3)
    fh.setLevel(getattr(logging, log_level, logging.INFO))
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, log_level, logging.INFO))
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

# Basic input sanitization helpers
def sanitize_text(value: str, max_len: int = 255):
    if not isinstance(value, str):
        return ''
    v = value.strip()
    return v[:max_len]

def validate_year(year):
    try:
        y = int(year)
        if 1900 <= y <= 2100:
            return y
        return None
    except Exception:
        return None

def to_int_in_range(value, default=10, min_v=1, max_v=100):
    try:
        v = int(value)
        if v < min_v:
            return min_v
        if v > max_v:
            return max_v
        return v
    except Exception:
        return default

def require_read_token():
    token = app.config.get('READ_API_TOKEN')
    if not token:
        return True
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        provided = auth.split(' ', 1)[1]
        if secrets.compare_digest(provided, token):
            return True
    logger.warning('Unauthorized access to stats endpoint from %s', request.remote_addr)
    return False

# CSRF utilities
def get_csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token

def verify_csrf():
    # Only enforce for modifying requests
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            logger.warning('CSRF validation failed')
            return False
    return True

@app.before_request
def before_request():
    # Ensure CSRF token exists in session
    get_csrf_token()
    # CSRF check
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        if not verify_csrf():
            return { 'status': 'danger', 'message': 'CSRF validation failed' }, 400

@app.after_request
def set_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Permissions-Policy'] = 'geolocation=()'
    # Relaxed CSP suitable for this app structure
    resp.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return resp

# Session cookie security (production values)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

# Database Models
class Movie(db.Model):
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    availability_status = db.Column(db.String(20), default='Available')
    rentals = db.relationship('Rental', backref='movie', lazy=True)

class Customer(db.Model):
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.Text, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rentals = db.relationship('Rental', backref='customer', lazy=True)

class Rental(db.Model):
    rental_id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.movie_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    rental_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    return_date = db.Column(db.Date)
    rental_status = db.Column(db.String(20), default='Not Returned')

class Admin(db.Model):
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# Initialize database
with app.app_context():
    db.create_all()
    # If using MySQL and tables already exist with smaller password columns, widen them
    if db_url.startswith('mysql'):
        try:
            parsed = urlparse(db_url)
            db_name = unquote(parsed.path.lstrip('/'))
            host = parsed.hostname or '127.0.0.1'
            port = parsed.port or 3306
            user = unquote(parsed.username or '')
            password = unquote(parsed.password or '')
            conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db_name)
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE `admin` MODIFY `password` VARCHAR(255) NOT NULL;")
                cur.execute("ALTER TABLE `customer` MODIFY `password` VARCHAR(255) NOT NULL;")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Could not alter password columns (may be fresh schema): {e}")
    # Create default admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin', password=generate_password_hash('admin123'))
        db.session.add(admin)
        db.session.commit()

    # Seed demo data (movies and a demo customer) if empty
    if Movie.query.count() == 0:
        demo_movies = [
            Movie(title='The Matrix', genre='Sci-Fi', release_year=1999, availability_status='Available'),
            Movie(title='Inception', genre='Sci-Fi', release_year=2010, availability_status='Available'),
            Movie(title='Interstellar', genre='Sci-Fi', release_year=2014, availability_status='Available'),
            Movie(title='The Dark Knight', genre='Action', release_year=2008, availability_status='Available'),
            Movie(title='Parasite', genre='Thriller', release_year=2019, availability_status='Available'),
        ]
        db.session.add_all(demo_movies)
        db.session.commit()

    if Customer.query.count() == 0:
        demo_customer = Customer(
            name='Demo User',
            email='demo@example.com',
            phone='1234567890',
            address='123 Demo Street',
            password=generate_password_hash('demo123')
        )
        db.session.add(demo_customer)
        db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            username = data.get('username','')
            password = data.get('password','')
        else:
            username = request.form['username']
            password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        logger.info('Admin login attempt: %s', username)
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.admin_id
            session['is_admin'] = True
            if request.is_json:
                return { 'status': 'success', 'message': 'Login successful', 'redirect': url_for('admin_dashboard') }
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
        if request.is_json:
            return { 'status': 'danger', 'message': 'Invalid credentials' }, 401
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    total_movies = Movie.query.count()
    total_customers = Customer.query.count()
    active_rentals = Rental.query.filter_by(rental_status='Not Returned').count()
    available_movies = Movie.query.filter_by(availability_status='Available').count()
    
    return render_template('admin_dashboard.html', 
                         total_movies=total_movies,
                         total_customers=total_customers,
                         active_rentals=active_rentals,
                         available_movies=available_movies)

@app.route('/admin/movies')
def admin_movies():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    movies = Movie.query.all()
    return render_template('admin_movies.html', movies=movies)

@app.route('/admin/movies/add', methods=['GET', 'POST'])
def add_movie():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            title = sanitize_text(data.get('title',''), 100)
            genre = sanitize_text(data.get('genre',''), 50)
            year = validate_year(data.get('release_year'))
            if not (title and genre and year):
                return { 'status': 'danger', 'message': 'Invalid input' }, 400
            movie = Movie(title=title, genre=genre, release_year=year, availability_status='Available')
            try:
                db.session.add(movie)
                db.session.commit()
                logger.info('Movie added: %s (%s)', movie.title, movie.release_year)
            except Exception as e:
                db.session.rollback()
                logger.exception('Failed to add movie')
                return { 'status': 'danger', 'message': 'Failed to add movie' }, 500
            return { 'status': 'success', 'message': 'Movie added successfully', 'movie_id': movie.movie_id, 'redirect': url_for('admin_movies') }
        else:
            title = sanitize_text(request.form['title'], 100)
            genre = sanitize_text(request.form['genre'], 50)
            year = validate_year(request.form['release_year'])
            if not (title and genre and year):
                flash('Invalid input', 'danger')
                return render_template('add_movie.html')
            movie = Movie(title=title, genre=genre, release_year=year, availability_status='Available')
            try:
                db.session.add(movie)
                db.session.commit()
                logger.info('Movie added: %s (%s)', movie.title, movie.release_year)
                flash('Movie added successfully!', 'success')
                return redirect(url_for('admin_movies'))
            except Exception:
                db.session.rollback()
                logger.exception('Failed to add movie')
                flash('Failed to add movie', 'danger')
                return render_template('add_movie.html')
    return render_template('add_movie.html')

@app.route('/admin/movies/edit/<int:id>', methods=['GET', 'POST'])
def edit_movie(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    movie = Movie.query.get_or_404(id)
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            if 'title' in data: movie.title = sanitize_text(data['title'], 100)
            if 'genre' in data: movie.genre = sanitize_text(data['genre'], 50)
            if 'release_year' in data:
                yr = validate_year(data['release_year'])
                if yr is None:
                    return { 'status': 'danger', 'message': 'Invalid year' }, 400
                movie.release_year = yr
            if 'availability_status' in data: movie.availability_status = sanitize_text(data['availability_status'], 20)
            try:
                db.session.commit()
                logger.info('Movie autosaved: id=%s', movie.movie_id)
            except Exception:
                db.session.rollback()
                logger.exception('Autosave failed for movie %s', movie.movie_id)
                return { 'status': 'danger', 'message': 'Autosave failed' }, 500
            return { 'status': 'success', 'message': 'Movie saved' }
        else:
            title = sanitize_text(request.form['title'], 100)
            genre = sanitize_text(request.form['genre'], 50)
            year = validate_year(request.form['release_year'])
            status = sanitize_text(request.form['availability_status'], 20)
            if not (title and genre and year and status):
                flash('Invalid input', 'danger')
                return render_template('edit_movie.html', movie=movie)
            movie.title = title
            movie.genre = genre
            movie.release_year = year
            movie.availability_status = status
            try:
                db.session.commit()
                logger.info('Movie updated: id=%s', movie.movie_id)
                flash('Movie updated successfully!', 'success')
                return redirect(url_for('admin_movies'))
            except Exception:
                db.session.rollback()
                logger.exception('Failed to update movie %s', movie.movie_id)
                flash('Failed to update movie', 'danger')
                return render_template('edit_movie.html', movie=movie)
    return render_template('edit_movie.html', movie=movie)

@app.route('/admin/movies/delete/<int:id>')
def delete_movie(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    movie = Movie.query.get_or_404(id)
    try:
        db.session.delete(movie)
        db.session.commit()
        logger.info('Movie deleted: id=%s', id)
        flash('Movie deleted successfully!', 'success')
    except Exception:
        db.session.rollback()
        logger.exception('Failed to delete movie %s', id)
        flash('Failed to delete movie', 'danger')
    return redirect(url_for('admin_movies'))

@app.route('/admin/customers')
def admin_customers():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    customers = Customer.query.all()
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/rentals')
def admin_rentals():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    rentals = Rental.query.all()
    return render_template('admin_rentals.html', rentals=rentals)

@app.route('/admin/rentals/add', methods=['GET', 'POST'])
def add_rental():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            movie_id = data.get('movie_id')
            customer_id = data.get('customer_id')
        else:
            movie_id = request.form['movie_id']
            customer_id = request.form['customer_id']
        
        movie = Movie.query.get(movie_id)
        if movie.availability_status == 'Available':
            rental = Rental(
                movie_id=movie_id,
                customer_id=customer_id,
                rental_date=datetime.now().date(),
                rental_status='Not Returned'
            )
            movie.availability_status = 'Rented'
            try:
                db.session.add(rental)
                db.session.commit()
                logger.info('Rental recorded: movie=%s customer=%s', movie_id, customer_id)
            except Exception:
                db.session.rollback()
                logger.exception('Failed to record rental movie=%s customer=%s', movie_id, customer_id)
                if request.is_json:
                    return { 'status': 'danger', 'message': 'Failed to record rental' }, 500
                else:
                    flash('Failed to record rental', 'danger')
                    return redirect(url_for('admin_rentals'))
            if request.is_json:
                return { 'status': 'success', 'message': 'Rental recorded successfully', 'redirect': url_for('admin_rentals') }
            else:
                flash('Rental recorded successfully!', 'success')
                return redirect(url_for('admin_rentals'))
        if request.is_json:
            return { 'status': 'danger', 'message': 'Movie is not available' }, 400
        else:
            flash('Movie is not available!', 'danger')
    
    movies = Movie.query.filter_by(availability_status='Available').all()
    customers = Customer.query.all()
    return render_template('add_rental.html', movies=movies, customers=customers)

@app.route('/admin/rentals/return/<int:id>')
def return_rental(id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    rental = Rental.query.get_or_404(id)
    rental.return_date = datetime.now().date()
    rental.rental_status = 'Returned'
    
    movie = Movie.query.get(rental.movie_id)
    movie.availability_status = 'Available'
    
    try:
        db.session.commit()
        logger.info('Rental returned: id=%s', id)
        flash('Movie returned successfully!', 'success')
    except Exception:
        db.session.rollback()
        logger.exception('Failed to mark rental returned %s', id)
        flash('Failed to mark as returned', 'danger')
    return redirect(url_for('admin_rentals'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('is_admin', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# Customer Routes
@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            name = sanitize_text(data.get('name',''), 100)
            email = sanitize_text(data.get('email',''), 100)
            phone = sanitize_text(data.get('phone',''), 15)
            address = sanitize_text(data.get('address',''), 255)
            pwd = data.get('password','')
            if not (name and email and phone and address and pwd):
                return { 'status': 'danger', 'message': 'Invalid input' }, 400
            customer = Customer(name=name, email=email, phone=phone, address=address, password=generate_password_hash(pwd))
            try:
                db.session.add(customer)
                db.session.commit()
                logger.info('Customer registered: %s', email)
            except Exception:
                db.session.rollback()
                logger.exception('Failed to register customer %s', email)
                return { 'status': 'danger', 'message': 'Registration failed' }, 500
            return { 'status': 'success', 'message': 'Registration successful', 'redirect': url_for('customer_login') }
        else:
            name = sanitize_text(request.form['name'], 100)
            email = sanitize_text(request.form['email'], 100)
            phone = sanitize_text(request.form['phone'], 15)
            address = sanitize_text(request.form['address'], 255)
            pwd = request.form['password']
            if not (name and email and phone and address and pwd):
                flash('Invalid input', 'danger')
                return render_template('customer_register.html')
            customer = Customer(name=name, email=email, phone=phone, address=address, password=generate_password_hash(pwd))
            try:
                db.session.add(customer)
                db.session.commit()
                logger.info('Customer registered: %s', email)
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('customer_login'))
            except Exception:
                db.session.rollback()
                logger.exception('Failed to register customer %s', email)
                flash('Registration failed', 'danger')
                return render_template('customer_register.html')
    return render_template('customer_register.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            email = data.get('email','')
            password = data.get('password','')
        else:
            email = request.form['email']
            password = request.form['password']
        customer = Customer.query.filter_by(email=email).first()
        
        if customer and check_password_hash(customer.password, password):
            session['customer_id'] = customer.customer_id
            if request.is_json:
                return { 'status': 'success', 'message': 'Login successful', 'redirect': url_for('customer_dashboard') }
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('customer_dashboard'))
        if request.is_json:
            return { 'status': 'danger', 'message': 'Invalid credentials' }, 401
        else:
            flash('Invalid credentials', 'danger')
    return render_template('customer_login.html')

@app.route('/customer/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer = Customer.query.get(session['customer_id'])
    available_movies = Movie.query.filter_by(availability_status='Available').all()
    return render_template('customer_dashboard.html', customer=customer, movies=available_movies)

@app.route('/customer/rentals')
def customer_rentals():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    rentals = Rental.query.filter_by(customer_id=session['customer_id']).all()
    return render_template('customer_rentals.html', rentals=rentals)

@app.route('/customer/rent/<int:movie_id>')
def rent_movie(movie_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    movie = Movie.query.get_or_404(movie_id)
    if movie.availability_status == 'Available':
        rental = Rental(
            movie_id=movie_id,
            customer_id=session['customer_id'],
            rental_date=datetime.now().date(),
            rental_status='Not Returned'
        )
        movie.availability_status = 'Rented'
        try:
            db.session.add(rental)
            db.session.commit()
            logger.info('Customer rented movie: movie=%s customer=%s', movie_id, session['customer_id'])
            flash('Movie rented successfully!', 'success')
        except Exception:
            db.session.rollback()
            logger.exception('Failed to rent movie=%s by customer=%s', movie_id, session['customer_id'])
            flash('Failed to rent movie', 'danger')
    else:
        flash('Movie is not available!', 'danger')
    return redirect(url_for('customer_dashboard'))

@app.route('/customer/logout')
def customer_logout():
    session.pop('customer_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/landing')
def landing_page():
    return render_template('landing.html', api_token=app.config.get('READ_API_TOKEN', ''))

@app.route('/api/landing_stats')
def api_landing_stats():
    if not require_read_token():
        return { 'status': 'danger', 'message': 'Unauthorized' }, 401
    limit = to_int_in_range(request.args.get('limit', 8), default=8, min_v=1, max_v=50)
    try:
        total_movies = Movie.query.count()
        available_movies = Movie.query.filter_by(availability_status='Available').count()
        total_customers = Customer.query.count()
        active_rentals = Rental.query.filter_by(rental_status='Not Returned').count()
        top = Movie.query.filter_by(availability_status='Available').order_by(Movie.release_year.desc()).limit(limit).all()
        payload = {
            'status': 'success',
            'server_time': datetime.utcnow().isoformat() + 'Z',
            'summary': {
                'total_movies': total_movies,
                'available_movies': available_movies,
                'total_customers': total_customers,
                'active_rentals': active_rentals,
            },
            'top_available': [
                {
                    'movie_id': m.movie_id,
                    'title': sanitize_text(m.title, 100),
                    'genre': sanitize_text(m.genre, 50),
                    'release_year': m.release_year,
                } for m in top
            ]
        }
        return payload
    except Exception:
        logger.exception('Failed to compute landing stats')
        return { 'status': 'danger', 'message': 'Failed to load stats' }, 500

if __name__ == '__main__':
    app.run(debug=True)