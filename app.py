import os
from flask import Flask, g, request,render_template,jsonify
import cx_Oracle
import time
import atexit

#load_dotenv()
app = Flask(__name__)
cached_data_cities = None
cached_data_railways = None
last_refresh = 0
CACHE_TTL_SECONDS = 60 * 60  # Cache for 1 hour


# === Create a global Oracle connection pool ===
dsn = cx_Oracle.makedsn("20.84.145.157", 1521, service_name="XEPDB1")
try:
    pool = cx_Oracle.SessionPool(
        user="SHRIRAM",
        password="Admin123",
        dsn=dsn,
        min=2,
        max=10,
        increment=1,
        threaded=True,
        getmode=cx_Oracle.SPOOL_ATTRVAL_WAIT
    )
except Exception as e:
    print(f"❌ Failed to create Oracle connection pool: {e}")
    exit(1)

# Close pool gracefully when app stops
atexit.register(lambda: pool.close())

# === Acquire a connection for each request ===
@app.before_request
def before_request():
    try:
        g.db = pool.acquire()
    except Exception as e:
        g.db = None
        print(f"❌ Error acquiring connection: {e}")

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db') and g.db:
        pool.release(g.db)

# === Error handler (500 and DB errors) ===
@app.errorhandler(Exception)
def handle_exception(e):
    print(f"❌ Unexpected error: {e}")
    return jsonify({"error": str(e)}), 500


def get_cities():
    print("Fetching cities from the database...")
    global cached_data_cities, last_refresh
    current_time = time.time()
    if cached_data_cities is not None and (current_time - last_refresh) < CACHE_TTL_SECONDS:
        print("Returning cached data.")
        return cached_data_cities

    print("Connecting to Oracle Database...")

    if not g.db:
        return {"error": "Database connection failed"}, 500
    try:
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT c.geonameid, c.name, c.country_code, c.location.sdo_point.y, c.location.sdo_point.x, c.population
            FROM cities c
            WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
            ORDER BY c.population DESC
            FETCH FIRST 1000 ROWS ONLY
        """)
        cities = [
            {
                "geonameid": record[0],
                "name": record[1],
                "country_code": record[2],
                "latitude": record[3],
                "longitude": record[4],
                "population": record[5]
            }
            for record in cursor.fetchall()
        ]
        last_refresh = time.time()
        cached_data_cities = cities
        print(f"Retrieved {len(cities)} cities from the database.")
        return cities

    except Exception as e:
        print(f"❌ Error fetching cities: {e}")
        return jsonify({"error": "Failed to query cities"}), 500

    finally:
        if cursor:
            cursor.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cities')
def cities():
    cities = get_cities()
    return jsonify(cities)


@app.route("/railways")
def get_railways():
    print("Fetching railways data...")
    global cached_data_railways, last_refresh
    current_time = time.time()
    print("Cached data:", cached_data_railways)
    if cached_data_railways is not None and (current_time - last_refresh) < CACHE_TTL_SECONDS:
        print("Returning cached data.")
        return cached_data_railways

    if not g.db:
        return {"error": "Database connection failed"}, 500
    
    try:
        cursor = g.db.cursor()
        cursor.execute("""
            SELECT id, name, country, length_km, type,
                rwdb_rr_id, mult_track, electric, other_code, category,
                disp_scale, add_field, featurecla, scalerank, natlscale,
                part, continent, geometry
                FROM (
                    SELECT *
                    FROM railways
                    WHERE geometry IS NOT NULL
                    ORDER BY DBMS_RANDOM.VALUE
                )
                WHERE ROWNUM <= 1000    
            """)
        results = []   
        for row in cursor:
            (
            gid, name, country, length_km, rail_type,
            rwdb_rr_id, mult_track, electric, other_code, category,
            disp_scale, add_field, featurecla, scalerank, natlscale,
            part, continent, geom
            ) = row

            # Extract ordinates from the geometry
            ordinates = geom.SDO_ORDINATES.aslist() if geom.SDO_ORDINATES else []
            coordinates = [(ordinates[i + 1], ordinates[i]) for i in range(0, len(ordinates), 2)]  
            # Leaflet expects [lat, lon], but SDO is (x=lon, y=lat)

            results.append({
            "id": gid,
            "name": name,
            "country": country,
            "length_km": length_km,
            "type": rail_type,
            "rwdb_rr_id": rwdb_rr_id,
            "mult_track": mult_track,
            "electric": electric,
            "other_code": other_code,
            "category": category,
            "disp_scale": disp_scale,
            "add_field": add_field,
            "featurecla": featurecla,
            "scalerank": scalerank,
            "natlscale": natlscale,
            "part": part,
            "continent": continent,
            "coordinates": coordinates
            })
        
        print(f"Retrieved {len(results)} railways from the database.")
        last_refresh = time.time()
        cached_data_railways = jsonify(results)
        return jsonify(results)

    except Exception as e:
        print(f"❌ Query failed: {e}")
        return jsonify({"error": "Failed to query railways"}), 500 

    finally:
        if cursor:
            cursor.close()

if __name__ == "__main__":
    app.run(debug=True)



