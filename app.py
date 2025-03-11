import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
import openai
import stripe

app = Flask(__name__)

# Load API Keys from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Replace with your actual Stripe Price ID
STRIPE_PRICE_ID = "price_1R0vKFFQW2MgVpygSrjEqD0n"  # Replace with the Price ID from Stripe dashboard

# Dummy user database (Replace with a real database later)
users = {"test_user": {"subscribed": False}}

@app.route("/")
def home():
    user_id = request.cookies.get("user_id")

    if not user_id:
        return render_template("login.html")  # Show login form if user isn't logged in

    return render_template("index.html")  # If logged in, show the chatbot

@app.route("/chat", methods=["POST"])
def chat():
    user_id = request.cookies.get("user_id")
    if not user_id:
        return jsonify({"reply": "⚠️ Please log in to chat."})

    # Check if user is subscribed
    if not users.get(user_id, {}).get("subscribed", False):
        return jsonify({"reply": "⚠️ You need a subscription to continue. Click below to subscribe."})

    user_message = request.json.get("message", "")
    
    response = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )

    chatbot_reply = response.choices[0].message.content
    return jsonify({"reply": chatbot_reply})

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
    user_id = request.cookies.get("user_id", "test_user")  # Get the user ID

    # Ensure the user exists in the dictionary before updating
    if user_id not in users:
        users[user_id] = {"subscribed": False}

    users[user_id]["subscribed"] = True  # Mark user as subscribed

    return redirect(url_for("home", success="1"))  # Redirect to chat page with success message

@app.route("/cancel")
def cancel():
    return "⚠️ Subscription was canceled. You can try again anytime."

if __name__ == "__main__":
    app.run(debug=True)
