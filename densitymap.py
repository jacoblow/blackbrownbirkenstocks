import pandas as pd
import folium
from folium.plugins import HeatMap

try:
    crime_data = pd.read_csv("shortenedSFcrimedata2_modified.csv")
except FileNotFoundError:
    print("Crime dataset not found. Please ensure the CSV file is in the correct location.")
    exit()


crime_data = crime_data.dropna(subset=["Latitude", "Longitude"])


heat_data = crime_data[["Latitude", "Longitude"]].values.tolist()


map_center = [37.7749, -122.4194]
crime_map = folium.Map(location=map_center, zoom_start=12)

custom_gradient = {
    # "0.3": 'blue',
    "0.2": 'lime',
    "0.4": 'yellow',
    "0.7": 'orange',
    "0.85": 'red',
    "1.0": 'darkred'
}


HeatMap(
    heat_data,
    radius=15,         
    blur=10,           
    min_opacity=0.3,   
    gradient=custom_gradient  
).add_to(crime_map)


output_file = "density_map.html"
crime_map.save(output_file)
print(f"Heatmap generated and saved to {output_file}")
