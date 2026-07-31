from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import secrets

app = Flask(__name__)

# 🔐 Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///secure_site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔐 Database
db = SQLAlchemy(app)

# 🔐 Rate Limiting
limiter = Limiter(app=app, key_func=get_remote_address)

# 🔐 CORS - W3Schools aur other domains allow
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 
    'https://www.w3schools.com,https://www.w3schools.com/tryit,http://localhost:5500,http://localhost:3000'
).split(',')
CORS(app, origins=ALLOWED_ORIGINS)

# 📝 Models
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(20), default='#3498db')
    font_size = db.Column(db.Integer, default=24)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'color': self.color,
            'font_size': self.font_size,
            'created_at': self.created_at.isoformat()
        }

# 🔐 User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 🔐 Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 🔐 Protected Admin View
class SecureAdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return render_template_string('''
            <h1>🔒 Access Denied</h1>
            <p>Please login to access admin panel</p>
            <a href="/login">Login Here</a>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
                a { display: inline-block; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        '''), 401

# 🔐 Admin Setup
admin = Admin(app, template_mode='bootstrap3')
admin.add_view(SecureAdminView(Message, db.session))

# 🔐 Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return '''
                <script>
                    window.location.href = '/admin';
                </script>
            '''
        return 'Invalid credentials', 401
    return '''
        <form method="post" style="max-width: 300px; margin: 100px auto; padding: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.1); border-radius: 10px;">
            <h2 style="text-align: center;">🔐 Login</h2>
            <input type="text" name="username" placeholder="Username" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px;">
            <input type="password" name="password" placeholder="Password" required style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px;">
            <button type="submit" style="width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">Login</button>
        </form>
        <style>
            body { font-family: Arial; background: #f5f5f5; margin: 0; padding: 20px; }
        </style>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out! <a href="/">Go Home</a>'

# 🔐 INTERNAL API - Hidden from frontend
@app.route('/internal/messages', methods=['GET'])
@limiter.limit("30 per minute")
def internal_get_messages():
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return jsonify([msg.to_dict() for msg in messages])

@app.route('/internal/messages', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def internal_create_message():
    data = request.json
    new_msg = Message(
        title=data['title'],
        content=data['content'],
        color=data.get('color', '#3498db'),
        font_size=data.get('font_size', 24)
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify(new_msg.to_dict()), 201

# 🔐 PUBLIC PROXY API - Frontend isko call karega
@app.route('/api/data', methods=['GET'])
@limiter.limit("60 per minute")
def public_get_data():
    try:
        return internal_get_messages()
    except Exception as e:
        return jsonify({'error': 'Something went wrong'}), 500

# 🔐 Admin Update Proxy
@app.route('/api/admin/update', methods=['POST'])
@limiter.limit("5 per minute")
def public_admin_update():
    api_key = request.headers.get('X-API-Key')
    if api_key != os.environ.get('ADMIN_API_KEY', 'your-secret-key'):
        return jsonify({'error': 'Unauthorized'}), 401
    return internal_create_message()

# 🔐 Health Check
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.utcnow().isoformat(),
        'cors_origins': ALLOWED_ORIGINS,
        'message_count': Message.query.count()
    })

# 🔐 Root Route
@app.route('/')
def home():
    return '''
        <h1>✅ Backend is Running!</h1>
        <p>🔐 Admin Panel: <a href="/admin">/admin</a></p>
        <p>📡 Public API: <a href="/api/data">/api/data</a></p>
        <p>💚 Health Check: <a href="/health">/health</a></p>
        <hr>
        <h3>🌐 CORS Allowed Origins:</h3>
        <ul>
            <li>https://www.w3schools.com</li>
            <li>https://www.w3schools.com/tryit</li>
            <li>http://localhost:5500</li>
            <li>http://localhost:3000</li>
        </ul>
        <hr>
        <p>📝 Total Messages: <strong id="msgCount">Loading...</strong></p>
        <script>
            fetch('/health')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('msgCount').textContent = data.message_count || 0;
                })
                .catch(() => {
                    document.getElementById('msgCount').textContent = 'Error';
                });
        </script>
    '''

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'SecurePass123!')
        if not User.query.filter_by(username=admin_username).first():
            admin_user = User(username=admin_username)
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Admin created: {admin_username}")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))