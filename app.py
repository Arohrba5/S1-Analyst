from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    companies = ["Servicetitan, Inc.", "Meta Platforms, Inc.", "Alphabet, Inc.", "Netflix, Inc."]
    return render_template('index.html', companies=companies)

if __name__ == "__main__":
    app.run(debug=True)