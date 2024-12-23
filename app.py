from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    companies = ["Servicetitan, Inc.", "Meta Platforms, Inc.", "Alphabet, Inc.", "Netflix, Inc."]
    return render_template('index.html', companies=companies)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use PORT if provided, otherwise default to 5000
    app.run(host="0.0.0.0", port=port)        # Use 0.0.0.0 to accept connections from any IP