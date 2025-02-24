# RoutesITrust: UCSB Datathon Project

RoutesITrust is a safe-route navigation tool developed for UCSB's Datathon. It integrates crime incident data with walking route information to help pedestrians choose the safest path in urban environments.

## Overview

RoutesITrust combines real-world crime data with alternative walking routes (retrieved via the Google Maps Directions API) to generate safety ratings for each option. Using interactive maps and heatmaps (powered by Folium), the tool visualizes risk along routes so users can make informed travel decisions.

## Features

- **Alternative Route Analysis:**  
  Compare multiple walking routes based on calculated safety scores.

- **Crime Data Integration:**  
  Leverages San Francisco crime reports to quantify risk along each route.

- **Interactive Visualizations:**  
  Displays routes and density heatmaps to highlight areas of concern.

- **Risk Scoring:**  
  Normalizes incident data against citywide crime trends for accurate route risk assessments.

- **User-Friendly Web Interface:**  
  Built with Flask for easy deployment and interaction.

## Note:

 - **The Google Map's API key will have low usage limits after the UCSB Datathon 2/23/2025.**
  Please contact me to test out this project on a greater scale, or grab your free google maps api key from https://developers.google.com/maps/documentation/javascript/get-api-key.
