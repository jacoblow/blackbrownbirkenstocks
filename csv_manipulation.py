import googlemaps
import folium
import pandas as pd
import numpy as np
from datetime import datetime
import os


api_url = api_url = "https://data.sfgov.org/resource/wg3w-h783.csv?$limit=1000&$order=Incident_Datetime%20desc"
new_data = pd.read_csv(api_url)

local_file = "shortenedSFcrimedata2_modified.csv"
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
    "Arson": 70,
    "Assault": 85,
    "Disorderly Conduct": 20,
    "Drug Offense": 55,
    "Drug Violation": 55,
    "Homicide": 100,
    "Human Trafficking, Commercial Sex Acts": 95,
    "Larceny Theft": 50,
    "Liquor Laws": 30,
    "Motor Vehicle Theft": 60,
    "Prostitution": 40,
    "Rape": 98,
    "Robbery": 90,
    "Sex Offense": 88,
    "Suspicious": 10,
    "Suspicious Occ": 10,
    "Traffic Collision": 35,
    "Traffic Violation Arrest": 25,
    "Weapons Carrying Etc": 85,
    "Weapons Offense": 90,
    "Stolen Property": 45
}

df["Incident_Weight"] = df["Incident Category"].map(weights)

df["Incident Datetime"] = pd.to_datetime(df["Incident Datetime"], errors='coerce')


def district_sum(dataframe):
    districts_crime_rates = dataframe.groupby("Police District")["Exponential_Score"].sum()
    return districts_crime_rates

district_sum(df)

print(district_sum(df)[1])
current_date = datetime.now()
gamma = 0.001
emvec = []

df["Exponential_Score"] = df["Incident_Weight"] * np.exp((-1) * gamma * (current_date - df["Incident Datetime"]).dt.days)
df = df.iloc[:, :37]

output_file_path = "~/Desktop/shortenedSFcrimedata2_modified.csv"
df.to_csv(output_file_path, index=False)

