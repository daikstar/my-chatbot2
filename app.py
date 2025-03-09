import os
from flask import Flask, request, jsonify, render_template
import openai

# Create Flask app
app = Flask(__name__)

# Create an OpenAI client using API key
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "")  # Get user input safely
        print(f"Received message: {user_message}")  # Debugging print

        # Call OpenAI's API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )

        chatbot_reply = response.choices[0].message.content  # Extract AI's response
        print(f"ChatGPT Response: {chatbot_reply}")  # Debugging print

        return jsonify({"reply": chatbot_reply})

    except Exception as e:
        print(f"Error: {str(e)}")  # Print error to terminal
        return jsonify({"reply": "An error occurred, please try again later."}), 500

if __name__ == "__main__":
    app.run(debug=True)
