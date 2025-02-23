import googlemaps
import folium
import pandas as pd
import numpy as np
from datetime import datetime
import os


api_url = api_url = "https://data.sfgov.org/resource/wg3w-h783.csv?$limit=1000&$order=Incident_Datetime%20desc"
new_data = pd.read_csv(api_url)


# Identify the local file in your CD
local_file = "shortenedSFcrimedata2_modified.csv"
local_file = os.path.expanduser(local_file)

if os.path.exists(local_file):
    local_data = pd.read_csv(local_file)
else:
    local_data = pd.DataFrame()

#Update Existing CSV with new, updated values
df = pd.concat([local_data, new_data], ignore_index=True)

# Identification of Unique Values, to measure and cutoff repeated data
unique_col = "Incident_ID"  
if unique_col in df.columns:
    df = df.drop_duplicates(subset=[unique_col])
else:
    df = df.drop_duplicates()


# Weight Dictionary for each Crime
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

# Crime Weight Column Creation
df["Incident_Weight"] = df["Incident Category"].map(weights)

#Convertion of "Incident Datetime" to Datetime format
df["Incident Datetime"] = pd.to_datetime(df["Incident Datetime"], errors='coerce')




# Initializing Variables for Exponential Scoring
current_date = datetime.now()
gamma = 0.01
emvec = []

# Creation of Exponential Score Column
df["Exponential_Score"] = df["Incident_Weight"] * np.exp((-1) * gamma * (current_date - df["Incident Datetime"]).dt.days)
df = df.iloc[:, :37]

# Function Summing the Crime Rates of Each District, Returning Crime Rate of the Districts over the Entire City (% from 0 to 1)
def district_sum(dataframe):
    districts_crime_rates = dataframe.groupby("Police District")["Exponential_Score"].sum()
    city_crime_rate = districts_crime_rates.sum()
    districts_over_city = {district: rate / city_crime_rate for district, rate in districts_crime_rates.items()}
    return districts_over_city



def district_risk(dsv):
    pmin = min(dsv.values())
    pmax = max(dsv.values())
    polar_diff = pmax-pmin
    if polar_diff == 0:
        return {district: 0 for district in dsv}

    alpha = 1.1
    power_curved_vec = {
        district: np.power(((score - pmin) / polar_diff), alpha)
        for district, score in dsv.items()}
    return power_curved_vec







# Sort dates in the file from newest to oldest
df = df.sort_values(by=df.columns[0], ascending=False)


# Exporting 2 Files


# Main File, Condensed
output_file_path = "~/Desktop/shortenedSFcrimedata2_modified.csv"
df.to_csv(output_file_path, index=False)

# Power Curved Vals
risk_scores = district_risk(district_sum(df))
pcdf = pd.DataFrame(risk_scores.items(), columns=["District", "Score"])
pcdf.to_csv("power_curved_values.csv", index=False)

