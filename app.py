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
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_id = request.cookies.get("user_id", "test_user")  # Dummy user system

        # Check if user is subscribed
        if not users.get(user_id, {}).get("subscribed", False):
            return jsonify({"reply": "⚠️ You need a subscription to continue. Click below to subscribe."})

        user_message = request.json.get("message", "")

        # Debugging print
        print(f"Received user message: {user_message}")

        # ✅ NEW OpenAI API format
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )

        chatbot_reply = response.choices[0].message.content

        # Debugging print
        print(f"Chatbot reply: {chatbot_reply}")

        return jsonify({"reply": chatbot_reply})

    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {str(e)}")  # Debugging
        return jsonify({"reply": f"⚠️ OpenAI Error: {str(e)}"})

    except Exception as e:
        print(f"❌ Chatbot Error: {str(e)}")  # Debugging
        return jsonify({"reply": "⚠️ An unexpected error occurred. Try again later."})

# Stripe Checkout Route
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,  # Use your actual Stripe Price ID
                "quantity": 1
            }],
            mode="subscription",
            success_url="https://my-chatbot2-ncek.onrender.com/success",
            cancel_url="https://my-chatbot2-ncek.onrender.com/cancel"
        )
        print("✅ Stripe session created:", session.id)  # Debugging
        return jsonify({"id": session.id})
    except Exception as e:
        print("Stripe Error:", str(e))  # Debugging print
        return jsonify({"error": str(e)}), 500

@app.route("/success")
def success():
    user_id = request.cookies.get("user_id", "test_user")  # Dummy user system
    users[user_id]["subscribed"] = True  # Mark user as subscribed

    return redirect(url_for("home", success="1"))  # Redirect to home with success message

@app.route("/cancel")
def cancel():
    return "⚠️ Subscription was canceled. You can try again anytime."

if __name__ == "__main__":
    app.run(debug=True)
