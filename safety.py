from flask import Flask, request, jsonify, render_template, session
import requests
import os
import polyline
import pandas as pd
import numpy as np
import folium

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for Flask session storage


# Store API Key in an environment variable
GOOGLE_MAPS_API_KEY = "AIzaSyCT5n2x3EIJh-fBw9GbuMWWKKj3PKClDgo"


@app.route("/")
def home():
    """ Renders the home page with an input form """
    return render_template("index.html")

from datetime import datetime, timedelta

@app.route("/safety_map", methods=["GET"])
def safety_map():

    # Retrieve stored routes and risk scores
    all_routes = session.get("all_routes", [])
    route_scores = session.get("route_scores", [])

    if not all_routes or not route_scores:
        return "No routes available. Please go back and enter locations first."

    try:
        crime_data = pd.read_csv("shortenedSFcrimedata2_modified.csv")
    except FileNotFoundError:
        return "Crime dataset not found. Please upload the file and restart Flask."

    print("Crime Data Columns:", crime_data.columns)  # Debugging step

    # Determine the safest route
    safest_route = min(route_scores, key=lambda x: x["total_risk_score"])["route_index"]

    # Center the map at the starting location
    map_center = all_routes[0]["coordinates"][0] if all_routes else (37.7749, -122.4194)  # Default to SF
    route_map = folium.Map(location=map_center, zoom_start=14)

    # Add walking routes to the map
    for route in all_routes:
        color = "green" if route["route_index"] == safest_route else "red"
        folium.PolyLine(route["coordinates"], color=color, weight=5, opacity=0.6).add_to(route_map)

        # Add Start & End markers for each route
        start_coords = route["coordinates"][0]
        end_coords = route["coordinates"][-1]

        folium.Marker(
            location=start_coords,
            icon=folium.Icon(color="blue", icon="play"),
            popup="Start Point"
        ).add_to(route_map)

        folium.Marker(
            location=end_coords,
            icon=folium.Icon(color="darkblue", icon="flag"),
            popup="End Point"
        ).add_to(route_map)

    # Get crimes near the route
    all_crime_data = pd.DataFrame()
    for route in all_routes:
        route_crimes = filter_crimes_by_route(crime_data, route["coordinates"])
        all_crime_data = pd.concat([all_crime_data, route_crimes], ignore_index=True)

    # Remove duplicate crimes
    all_crime_data = all_crime_data.drop_duplicates()

    # Convert Incident Datetime column to datetime object
    all_crime_data["Incident Datetime"] = pd.to_datetime(all_crime_data["Incident Datetime"], errors="coerce")

    # Define the time threshold for "past week"
    one_week_ago = datetime.now() - timedelta(days=7)

    # Filter crimes:
    filtered_crimes = all_crime_data[
        ((all_crime_data["Exponential_Score"] > 80) |  # Any crime with score > 80
         ((all_crime_data["Exponential_Score"] > 55) & (all_crime_data["Incident Datetime"] >= one_week_ago)))  # Past week & above 55
    ]

    # Add crime markers with better visibility
    for _, row in filtered_crimes.iterrows():
        crime_score = row["Exponential_Score"]

        # Assign severity level & marker size
        if crime_score > 80:
            crime_color = "red"
            size = 6
        elif crime_score > 55 and row["Incident Datetime"] >= one_week_ago:
            crime_color = "yellow"
            size = 6
        else:
            continue  # Skip crimes not in the criteria

        # Ensure all fields exist and are non-null
        crime_type = row["Incident Category"] if pd.notna(row["Incident Category"]) else "Unknown Crime"
        crime_desc = row["Incident Description"] if pd.notna(row["Incident Description"]) else "No Description"
        crime_time = row["Incident Datetime"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["Incident Datetime"]) else "Unknown Time"

        # Tooltip: Show both Time & Description on hover
        tooltip_text = f"{crime_desc} | {crime_time}"

        # Add enhanced crime marker with reduced opacity for readability
        folium.CircleMarker(
            location=(row["Latitude"], row["Longitude"]),
            radius=size,
            color="black",
            fill=True,
            fill_color=crime_color,
            fill_opacity=0.9,  # Reduced opacity for better map readability
            popup=folium.Popup(f"""
                <b>🚨 {crime_type}</b><br>
                <b>Description:</b> {crime_desc}<br>
                <b>Time:</b> {crime_time}<br>
                <b>Score:</b> {crime_score}<br>
                <b>Location:</b> ({row['Latitude']}, {row['Longitude']})
            """, max_width=300),
            tooltip=tooltip_text,
        ).add_to(route_map)

    # Save map to an HTML file
    map_path = "templates/safety_map.html"
    route_map.save(map_path)

    return render_template("safety_map.html")



def calculate_weighted_route_score(filtered_crimes):
    """
    Computes a weighted crime score for a specific route using log normalization.
    
    Parameters:
    filtered_crimes (pd.DataFrame): DataFrame containing crimes along a route with 'Exponential_Score'.

    Returns:
    float: Weighted crime score for the route.
    """
    # Compute total crime score and count of crimes along the route
    total_exponential_score = filtered_crimes["Exponential_Score"].sum()
    total_crimes = len(filtered_crimes)

    # Normalize using log to dampen extreme values
    if total_crimes > 0:
        weighted_score = total_exponential_score / np.log1p(total_crimes)  # log1p(x) = log(1 + x)
    else:
        weighted_score = 0

    return round(weighted_score, 2)

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

def calculate_crime_score(crime_df, min_max_coords):
    """
    Calculates a crime score for the bounding box defined by min and max latitude/longitude.
    """
    min_lat, max_lat = min_max_coords["min_latitude"], min_max_coords["max_latitude"]
    min_lng, max_lng = min_max_coords["min_longitude"], min_max_coords["max_longitude"]

    # Filter crimes within the bounding box
    crimes_in_box = crime_df[
        (crime_df["Latitude"].between(min_lat, max_lat)) &
        (crime_df["Longitude"].between(min_lng, max_lng))
    ]

    # Sum the exponential scores to get the total risk score in the bounding box
    total_crime_score = crimes_in_box["Exponential_Score"].sum()

    return total_crime_score

def filter_crimes_by_route(crime_df, route_coordinates, lat_range=0.0002326, lng_range=0.0002818):
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
    Computes a weighted risk score for each route based on nearby crimes.
    Stores data in session so it can be accessed by /safety_map.
    """
    origin = request.form.get("origin")
    destination = request.form.get("destination")

    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400


    # Request Google Maps Directions API with waypoints
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode=walking&alternatives=true&key={GOOGLE_MAPS_API_KEY}"
    
    response = requests.get(url, timeout=10)
    data = response.json()

    if "error_message" in data:
        return jsonify({"error": data["error_message"]}), 400

    if not data.get("routes"):
        return jsonify({"error": "No pedestrian routes found"}), 400

    # Load crime dataset
    try:
        crime_data = pd.read_csv("shortenedSFcrimedata2_modified.csv")
    except FileNotFoundError:
        return jsonify({"error": "Crime dataset not found"}), 500

    all_routes = []
    route_crime_data = []
    route_scores = []

    all_route_coordinates = []

    for idx, route in enumerate(data["routes"]):
        route_coordinates = []

        for leg in route["legs"]:
            for step in leg["steps"]:
                step_polyline = step["polyline"]["points"]
                step_points = polyline.decode(step_polyline)

                sampled_points = step_points[::3]  # Sample every 3rd point
                
                for lat, lng in sampled_points:
                    route_coordinates.append((lat, lng))
                    all_route_coordinates.append((lat, lng))

        # Store route details
        all_routes.append({
            "route_index": idx + 1,
            "summary": route.get("summary", "No Summary"),
            "distance": route["legs"][0]["distance"]["text"],
            "duration": route["legs"][0]["duration"]["text"],
            "coordinates": route_coordinates
        })

        # Filter crimes along this route
        filtered_crimes = filter_crimes_by_route(crime_data, route_coordinates)

        # Compute weighted crime score for this route
        total_exponential_score = filtered_crimes["Exponential_Score"].sum()
        # total_crimes = len(filtered_crimes)

        #weighted_route_score = total_exponential_score / np.log1p(total_crimes) if total_crimes > 0 else 0

        route_scores.append({"route_index": idx + 1, "total_risk_score": round(total_exponential_score, 2)})

        route_crime_data.append({"route_index": idx + 1, "crimes": filtered_crimes})

    min_max_coords = find_min_max_coordinates(all_route_coordinates)

    area_crimes = crime_data[
            (crime_data["Latitude"].between(min_max_coords["min_latitude"] + 0.0002326, min_max_coords["max_latitude"] - 0.0002326)) &
            (crime_data["Longitude"].between(min_max_coords["min_longitude"] + 0.0002818, min_max_coords["max_longitude"]) - 0.0002818)
        ]

    area_crime_score = area_crimes["Exponential_Score"].sum()

    total_crime_score  = crime_data["Exponential_Score"].sum()

    # Normalize the risk scores correctly
    for route in route_scores:
        total_risk_score = route["total_risk_score"]  # Extract numeric value

        # Prevent division by zero
        if area_crime_score == 0 or total_crime_score == 0:
            normalized_score = 10  # Assign a default value if no crimes are found
        else:
            normalized_score = (
                10 - ((1.5 * (total_risk_score / area_crime_score)) +
                ((80*total_risk_score) / total_crime_score) +
                2 * (area_crime_score / total_crime_score))
            )

        # Store the normalized score back into the dictionary
        route["normalized_score"] = round(normalized_score, 2)

    # Store results in session for later use
    session["all_routes"] = all_routes
    session["route_scores"] = route_scores  

    # Convert crime tables for display (only showing the head)
    crime_tables = {
        route_data["route_index"]: route_data["crimes"].head(10).to_html(classes="table table-striped", index=False)
        for route_data in route_crime_data
    }

    # Display risk scores
    risk_scores_df = pd.DataFrame(route_scores)
    risk_scores_html = risk_scores_df.to_html(classes="table table-striped", index=False)

    return render_template(
        "routes.html",
        routes=all_routes,
        crime_tables=crime_tables,
        risk_scores_html=risk_scores_html
    )


if __name__ == "__main__":
    app.run(debug=True)
