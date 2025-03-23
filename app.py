import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
import openai
import stripe
import json

app = Flask(__name__)

# Database configuration (PostgreSQL for production, SQLite for local testing)
if "DATABASE_URL" in os.environ:  
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://", 1)
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///llc_users.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # ✅ Ensure migrations work

with app.app_context():
    try:
        upgrade()
        print("✅ Database migrations applied successfully!")
    except Exception as e:
        print(f"⚠️ Database migration failed: {str(e)}")

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
        user = User(username=user_id, subscribed=False, progress=json.dumps({}))
        db.session.add(user)
        db.session.commit()

    # Load or initialize progress
    progress_data = json.loads(user.progress)

    # Build conversation context
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful and concise expert in California LLC formation. "
                "Answer with clear, friendly, step-by-step guidance. "
                "Keep responses under 100 words. Use numbered or bulleted lists only when necessary. "
                "Avoid repeating all steps at once unless the user specifically asks for it."
            )
        }
    ]

    # Add prior progress summary if available
    if "steps_completed" in progress_data:
        messages.append({
            "role": "assistant",
            "content": f"So far, you've completed: {', '.join(progress_data['steps_completed'])}."
        })

    messages.append({"role": "user", "content": user_message})

    # OpenAI Chat API call
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        reply = response.choices[0].message.content

        # Save last message and reply
        progress_data["last_message"] = user_message
        progress_data["last_reply"] = reply

        # Make sure steps_completed is a list before appending
        if "steps_completed" not in progress_data or not isinstance(progress_data["steps_completed"], list):
            progress_data["steps_completed"] = []

        # Optional: Auto-tag a completed step if GPT confirms one
        for step in ["Choose a name", "File Articles", "Appoint registered agent", "Create Operating Agreement", "Get EIN", "File licenses", "Ongoing compliance"]:
            if step.lower() in reply.lower() and step not in progress_data["steps_completed"]:
                progress_data["steps_completed"].append(step)
                break

        user.progress = json.dumps(progress_data)
        db.session.commit()

        return jsonify({"reply": reply})

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

# check db schema
@app.route("/check-db-schema")
def check_db_schema():
    try:
        column_names = [col.name for col in db.metadata.tables['user'].columns]
        return jsonify({"columns": column_names})
    except Exception as e:
        return jsonify({"error": str(e)})
