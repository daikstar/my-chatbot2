import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import openai
import stripe

app = Flask(__name__)

# Database configuration (PostgreSQL for production, SQLite for local testing)
if "DATABASE_URL" in os.environ:  
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://", 1)
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///llc_users.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # ✅ Ensure migrations work

# OpenAI & Stripe API Keys
openai.api_key = os.getenv("OPENAI_API_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Stripe Price IDs
STRIPE_PRICE_ID = "price_1R0vKFFQW2MgVpygSrjEqD0n"  # Replace with actual price ID

# Define User model
class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}  # ✅ Fix table conflicts

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    subscribed = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Text, default="{}")  # Store user's progress as JSON

# Create database tables (ONLY for SQLite)
if "DATABASE_URL" not in os.environ:
    with app.app_context():
        db.create_all()

# Homepage
@app.route("/")
def home():
    return render_template("index.html")

# Chat endpoint for LLC formation guidance
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    user_id = request.cookies.get("user_id", "guest")

    # Retrieve or create user
    user = User.query.filter_by(username=user_id).first()
    if not user:
        user = User(username=user_id, subscribed=False)
        db.session.add(user)
        db.session.commit()

    # Generate response using OpenAI
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert in LLC formation, guiding users through setting up an LLC in California step by step."},
                {"role": "user", "content": user_message}
            ]
        )
        chatbot_reply = response.choices[0].message.content

        return jsonify({"reply": chatbot_reply})

    except openai.OpenAIError as e:
        return jsonify({"reply": f"⚠️ OpenAI API Error: {str(e)}"})

# Subscription status check
@app.route("/subscription-status")
def subscription_status():
    user_id = request.cookies.get("user_id", "guest")
    user = User.query.filter_by(username=user_id).first()
    return jsonify({"subscribed": user.subscribed if user else False})

# Stripe checkout session
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=url_for("success", _external=True),
            cancel_url=url_for("cancel", _external=True),
        )
        return jsonify({"id": session.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Subscription success
@app.route("/success")
def success():
    user_id = request.cookies.get("user_id", "guest")
    user = User.query.filter_by(username=user_id).first()
    if user:
        user.subscribed = True
        db.session.commit()
    return redirect(url_for("home", success="1"))

# Subscription cancel
@app.route("/cancel")
def cancel():
    return "⚠️ Subscription was canceled. You can try again anytime."

if __name__ == "__main__":
    app.run(debug=True)
