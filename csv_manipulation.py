import googlemaps
import folium
import pandas as pd
import numpy as np
from datetime import datetime
import os


api_url = api_url = "https://data.sfgov.org/resource/wg3w-h783.csv?$limit=1000&$order=Incident_Datetime%20desc"
new_data = pd.read_csv(api_url)

local_file = "~/Desktop/shortenedSFcrimedata2_modified.csv"
local_file = os.path.expanduser(local_file)

if os.path.exists(local_file):
    local_data = pd.read_csv(local_file)
else:
    local_data = pd.DataFrame()

df = pd.concat([local_data, new_data], ignore_index=True)

unique_col = "Incident_ID"  
if unique_col in df.columns:
    df = df.drop_duplicates(subset=[unique_col])
else:
    df = df.drop_duplicates()



weights = {
    "Arson": 40,
    "Assault": 90,
    "Disorderly Conduct": 10,
    "Drug Offense": 65,
    "Drug Violation": 65,
    "Homicide": 100,
    "Human Trafficking, Commercial Sex Acts": 70,
    "Larceny Theft": 40,
    "Liquor Laws": 25,
    "Motor Vehicle Theft": 50,
    "Prostitution": 60,
    "Rape": 92,
    "Robbery": 90,
    "Sex Offense": 75,
    "Suspicious": 8,
    "Suspicious Occ": 8,
    "Traffic Collision": 20,
    "Traffic Violation Arrest": 30,
    "Weapons Carrying Etc": 90,
    "Weapons Offense": 90,
    "Stolen Property": 30
}

df["Incident_Weight"] = df["Incident Category"].map(weights)

df["Incident Datetime"] = pd.to_datetime(df["Incident Datetime"], errors='coerce')


current_date = datetime.now()
gamma = 0.001
emvec = []

df["Exponential_Score"] = df["Incident_Weight"] * np.exp((-1) * gamma * (current_date - df["Incident Datetime"]).dt.days)
df = df.iloc[:, :37]

output_file_path = "~/Desktop/shortenedSFcrimedata2_modified.csv"
df.to_csv(output_file_path, index=False)




