from flask import Flask, request, jsonify, render_template
import requests
import os
import polyline
import folium

app = Flask(__name__)

# Store API Key in an environment variable
GOOGLE_MAPS_API_KEY = "AIzaSyCT5n2x3EIJh-fBw9GbuMWWKKj3PKClDgo"

@app.route("/get_routes", methods=["GET"])
def get_routes():
    origin = request.args.get("origin")
    destination = request.args.get("destination")

    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400

    if not GOOGLE_MAPS_API_KEY:
        return jsonify({"error": "Missing Google Maps API Key"}), 500

    # Google Maps Directions API URL
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&alternatives=true&key={GOOGLE_MAPS_API_KEY}"

    response = requests.get(url)
    data = response.json()

    # Check for API errors
    if "error_message" in data:
        return jsonify({"error": data["error_message"]}), 400

    # Extract up to 3 routes
    routes = []
    for i, route in enumerate(data.get("routes", [])[:3]):
        routes.append({
            "summary": route.get("summary", "No Summary"),
            "distance": route["legs"][0]["distance"]["text"],
            "duration": route["legs"][0]["duration"]["text"],
            "polyline": route["overview_polyline"]["points"]
        })

    return jsonify(routes)

@app.route("/")
def home():
    """ Renders the home page with an input form """
    return render_template("index.html")

@app.route("/multiple_routes", methods=["POST"])
def get_multiple_routes():
    """
    Fetches multiple alternative walking routes and decodes their detailed coordinates.
    Accepts user input from an HTML form.
    """
    origin = request.form.get("origin")
    destination = request.form.get("destination")

    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400

    # Google Maps Directions API URL with `alternatives=true` to get multiple routes
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode=walking&alternatives=true&key={GOOGLE_MAPS_API_KEY}"
    
    response = requests.get(url)
    data = response.json()

    if "error_message" in data:
        return jsonify({"error": data["error_message"]}), 400

    if not data.get("routes"):
        return jsonify({"error": "No pedestrian routes found"}), 400

    # Extract detailed coordinates for multiple routes
    all_routes = []
    
    for idx, route in enumerate(data["routes"]):
        route_coordinates = []

        for leg in route["legs"]:
            for step in leg["steps"]:
                # Decode polyline from each step
                step_polyline = step["polyline"]["points"]
                step_points = polyline.decode(step_polyline)  # Returns a list of (lat, lng) tuples
                
                for lat, lng in step_points:
                    route_coordinates.append((lat, lng))  # Store as tuple

        # Store each route separately
        all_routes.append({
            "route_index": idx + 1,  # Ensuring index starts from 1
            "summary": route.get("summary", "No Summary"),
            "distance": route["legs"][0]["distance"]["text"],
            "duration": route["legs"][0]["duration"]["text"],
            "coordinates": route_coordinates  # List of tuples
        })

    return render_template("routes.html", routes=all_routes)

if __name__ == "__main__":
    app.run(debug=True)
