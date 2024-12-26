from flask import Flask, render_template, request, jsonify
import os  # Import the 'os' module to access environment variables
import psycopg2  # To connect to PostgreSQL

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def cik_lookup():
    return render_template('about.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use PORT if provided, otherwise default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)        # Use 0.0.0.0 to accept connections from any IP