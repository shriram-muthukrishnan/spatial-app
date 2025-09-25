# Spatial Web App

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10-green.svg)]()

## Overview
This is a **spatial web application** built on top of **Oracle databases** to provide an easy and interactive way to learn the geography of the Earth. The web app leverages **OpenStreetMap** for rendering the world map, with geometries such as **cities, railway lines, and countries** painted on top.  

Anyone above **5 years of age** can use this app to explore **country borders, capitals, and flags** interactively, rather than memorizing them from textbooks.

**Access the web app here:** https://world-cities-landmarks-argkhhdec4hacbap.centralus-01.azurewebsites.net/

---

## Features / What You Can Do

- **Map Controls:** Use the icons on the side of the map to **zoom in, zoom out**, and **reset the zoom**.  

- **Cities Section:**  
  - Displays popular cities across the world.  
  - If you know where a city is located, you can zoom in to check.  
  - Click on the location icon to view more details such as **population** and **nearby major cities**.  
  - If unsure, use the **search box** to locate the city instantly.  
  - Reset the zoom to see the city’s position relative to the overall world map.  

- **Countries Section:**  
  - Click on a country to see its **capital** and **flag**.  
  - The app covers a limited set of countries, making it easy and fun to **learn quickly**.  

- **Railways Section:**  
  - Red lines are painted across the map, each representing an actual **railway line** on Earth.  
  - Each line consists of **thousands of points**, and rendering them efficiently was challenging.  
  - Currently, the app lists the existing railway lines worldwide. Future enhancements may expand functionality here.

---

## Technical Details

- Preprocessing **SDO geometries as WKT** and **asynchronously loading chunks** allows for a faster experience than querying and rendering all geometries on the fly.  
- The app efficiently handles **large spatial datasets** while keeping the map interactive.  

---

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript (Leaflet / Mapbox)  
- **Backend:** Flask  
- **Database:** Oracle Database with spatial tables  
- **Data Processing:** Python scripts for geometry preprocessing and loading  

---

## License
This project is licensed under the [MIT License](LICENSE).

