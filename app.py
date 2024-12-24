from flask import Flask, render_template, request, jsonify
import os  # Import the 'os' module to access environment variables
import psycopg2  # To connect to PostgreSQL

app = Flask(__name__)

# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL")  # Fetch the DATABASE_URL from environment variables
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')  # Establish a connection to the database
    cursor = conn.cursor()  # Create a cursor for executing queries
except Exception as e:
    print(f"Error connecting to the database: {e}")  # Log connection errors

@app.route('/')
def home():
    # Render the homepage template with an empty dropdown initially
    return render_template('index.html')

@app.route('/get_companies', methods=['GET'])
def get_companies():
    # Get the user's query from the AJAX request
    query = request.args.get('query', '').strip()
    
    if not query:
        return jsonify([])  # Return an empty list if no query is provided

    try:
        # Query the database to find matching company names
        cursor.execute("""
            SELECT company_name
            FROM cik_lookup
            WHERE company_name ILIKE %s
            LIMIT 10;
        """, (f"{query}%",))
        results = [row[0] for row in cursor.fetchall()]
        return jsonify(results)  # Send results back as JSON
    except Exception as e:
        print(f"Error fetching data from the database: {e}")
        return jsonify([])  # Return an empty list if there’s an error

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use PORT if provided, otherwise default to 5000
    app.run(host="0.0.0.0", port=port)        # Use 0.0.0.0 to accept connections from any IP