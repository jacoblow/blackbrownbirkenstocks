from flask import Flask, request, jsonify, render_template
import requests
import os
import polyline
import pandas as pd

app = Flask(__name__)

# Store API Key in an environment variable
GOOGLE_MAPS_API_KEY = "AIzaSyCT5n2x3EIJh-fBw9GbuMWWKKj3PKClDgo"


@app.route("/")
def home():
    """ Renders the home page with an input form """
    return render_template("index.html")

def find_min_max_coordinates(all_coordinates):
    """
    Finds the minimum and maximum latitude and longitude values from a list of coordinate tuples.
    """
    if not all_coordinates:
        return {"error": "No coordinates found."}

    min_lat = min(all_coordinates, key=lambda x: x[0])[0]
    max_lat = max(all_coordinates, key=lambda x: x[0])[0]
    min_lng = min(all_coordinates, key=lambda x: x[1])[1]
    max_lng = max(all_coordinates, key=lambda x: x[1])[1]

    return {
        "min_latitude": min_lat,
        "max_latitude": max_lat,
        "min_longitude": min_lng,
        "max_longitude": max_lng
    }

def filter_crimes_by_route(crime_df, route_coordinates, lat_range=0.001, lng_range=0.001):
    """
    Filters crimes that fall within a specified range of any route coordinates.
    Uses explicit iteration instead of vectorized operations.
    
    Parameters:
    crime_df (pd.DataFrame): DataFrame containing crime data with 'Latitude' and 'Longitude' columns.
    route_coordinates (list of tuples): List of (latitude, longitude) pairs representing the route.
    lat_range (float): Latitude tolerance range.
    lng_range (float): Longitude tolerance range.

    Returns:
    pd.DataFrame: Filtered DataFrame containing crimes that fall within the specified range.
    """
    filtered_crimes = pd.DataFrame(columns=crime_df.columns)  # Create an empty DataFrame

    for lat, lng in route_coordinates:
        subset = crime_df[
            (crime_df["Latitude"].between(lat - lat_range, lat + lat_range)) &
            (crime_df["Longitude"].between(lng - lng_range, lng + lng_range))
        ]
        filtered_crimes = pd.concat([filtered_crimes, subset], ignore_index=True)  # Append matching crimes

    return filtered_crimes.drop_duplicates()  # Remove duplicates if any crime matches multiple route points

@app.route("/multiple_routes", methods=["POST"])
def get_multiple_routes():
    """
    Fetches multiple alternative walking routes and decodes their detailed coordinates.
    Accepts user input from an HTML form and filters nearby crimes.
    Displays crime data separately for each route.
    """
    origin = request.form.get("origin")
    destination = request.form.get("destination")

    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400

    # Google Maps Directions API URL with `alternatives=true` to get multiple routes
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode=walking&alternatives=true&key={GOOGLE_MAPS_API_KEY}"
    
    response = requests.get(url, timeout=10)
    data = response.json()

    if "error_message" in data:
        return jsonify({"error": data["error_message"]}), 400

    if not data.get("routes"):
        return jsonify({"error": "No pedestrian routes found"}), 400

    # Load crime dataset (Replace with actual CSV file path)
    crime_data = pd.read_csv("shortenedSFcrimedata2_modified.csv")  # Ensure the CSV file exists

    # Extract detailed coordinates for multiple routes
    all_routes = []
    route_crime_data = []  # Store crime data separately for each route
    route_scores = []

    for idx, route in enumerate(data["routes"]):
        route_coordinates = []

        for leg in route["legs"]:
            for step in leg["steps"]:
                # Decode polyline from each step
                step_polyline = step["polyline"]["points"]
                step_points = polyline.decode(step_polyline)  # Returns a list of (lat, lng) tuples

                sampled_points = step_points[::3]  # Sample every 3rd point
                
                for lat, lng in sampled_points:
                    route_coordinates.append((lat, lng))  # Store as tuple

        # Store each route separately
        all_routes.append({
            "route_index": idx + 1,  # Ensuring index starts from 1
            "summary": route.get("summary", "No Summary"),
            "distance": route["legs"][0]["distance"]["text"],
            "duration": route["legs"][0]["duration"]["text"],
            "coordinates": route_coordinates  # List of tuples
        })

        # Filter crime data for this specific route
        filtered_crimes = filter_crimes_by_route(crime_data, route_coordinates)

        total_risk_score = filtered_crimes["Exponential_Score"].sum()
        route_scores.append({"route_index": idx + 1, "total_risk_score": total_risk_score})

        route_crime_data.append({"route_index": idx + 1, "crimes": filtered_crimes})

    # Compute min and max latitude/longitude values
    min_max_coords = find_min_max_coordinates([coord for route in all_routes for coord in route["coordinates"]])

    crime_tables = {
        route_data["route_index"]: route_data["crimes"].to_html(classes="table table-striped", index=False)
        for route_data in route_crime_data
    }

    risk_scores_df = pd.DataFrame(route_scores)
    risk_scores_html = risk_scores_df.to_html(classes="table table-striped", index=False)

    return render_template(
        "routes.html",
        routes=all_routes,
        min_max_coords=min_max_coords,
        crime_tables=crime_tables,
        risk_scores_html=risk_scores_html
    )

if __name__ == "__main__":
    app.run(debug=True)
