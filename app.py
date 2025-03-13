import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import openai
import stripe

app = Flask(__name__)

# Configure the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subscriptions.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    subscribed = db.Column(db.Boolean, default=False)
    messages_used = db.Column(db.Integer, default=0)

# Load API Keys from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Replace with your actual Stripe Price ID
STRIPE_PRICE_ID = "price_1R0vKFFQW2MgVpygSrjEqD0n"  # Replace with the Price ID from Stripe dashboard

# Dummy user database (Replace with a real database later)
users = {"test_user": {"subscribed": False}}
FREE_TRIAL_LIMIT = 3

@app.route("/")
def home():
    user_id = request.cookies.get("user_id")

    if not user_id:
        return render_template("login.html")  # Show login form if user isn't logged in

    return render_template("index.html")  # If logged in, show the chatbot

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_id = request.cookies.get("user_id")
        if not user_id:
            return jsonify({"reply": "⚠️ Please log in to chat."})

        # Check if the user exists in the database
        user = User.query.filter_by(username=user_id).first()

        # If user doesn't exist, create them with a free trial
        if not user:
            user = User(username=user_id, subscribed=False, messages_used=0)
            db.session.add(user)
            db.session.commit()

        # Check if the user is subscribed
        if not user.subscribed:
            if user.messages_used >= FREE_TRIAL_LIMIT:
                return jsonify({"reply": "⚠️ Free trial limit reached! Subscribe to continue chatting."})

            # Increase free message count
            user.messages_used += 1
            db.session.commit()

        user_message = request.json.get("message", "")

        # ✅ OpenAI API call
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )

        chatbot_reply = response.choices[0].message.content
        return jsonify({"reply": chatbot_reply})

    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {str(e)}")  # Debugging
        return jsonify({"reply": f"⚠️ OpenAI Error: {str(e)}"})

    except Exception as e:
        print(f"❌ Chatbot Error: {str(e)}")  # Debugging
        return jsonify({"reply": "⚠️ An unexpected error occurred. Try again later."})


# Check Subscription status
@app.route("/subscription-status")
def subscription_status():
    user_id = request.cookies.get("user_id", "test_user")  # Dummy user system
    is_subscribed = users.get(user_id, {}).get("subscribed", False)
    return jsonify({"subscribed": is_subscribed})

# Stripe Checkout Route
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.json  # Get data from frontend
        plan = data.get("plan")  # Retrieve selected plan

        # Stripe Price IDs (Replace these with your actual IDs)
        price_ids = {
            "basic": "price_1R1KpBFQW2MgVpygh8S4eJwv",    # Replace with your Basic plan price ID
            "pro": "price_1R1KpRFQW2MgVpygyxxQNohs",      # Replace with your Pro plan price ID
            "premium": "price_1R1KpgFQW2MgVpyg9okwRgqk"   # Replace with your Premium plan price ID
        }

        if plan not in price_ids:
            return jsonify({"error": "Invalid plan selected."}), 400

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_ids[plan],  # Use selected plan's price ID
                "quantity": 1
            }],
            mode="subscription",
            success_url="https://my-chatbot2-ncek.onrender.com/success",
            cancel_url="https://my-chatbot2-ncek.onrender.com/cancel"
        )

        return jsonify({"id": session.id})

    except Exception as e:
        print("❌ Stripe Error:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500

@app.route("/success")
def success():
    user_id = request.cookies.get("user_id")

    if user_id:
        user = User.query.filter_by(username=user_id).first()
        if user:
            user.subscribed = True
            db.session.commit()

    return redirect(url_for("home", success="1"))

@app.route("/cancel")
def cancel():
    return "⚠️ Subscription was canceled. You can try again anytime."

if __name__ == "__main__":
    app.run(debug=True)
