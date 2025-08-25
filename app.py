import os
from flask import stream_with_context,Response
from flask import Flask,g,request,render_template,jsonify
import oracledb
import json
from shapely import wkt
from shapely.geometry import mapping
import time
import atexit
import traceback
from io import StringIO

app = Flask(__name__)
# === Configuration ===
cached_data_cities = None
cached_data_railways = None
last_refresh_cities = 0
last_refresh_railways = 0
CACHE_TTL_SECONDS = 60 * 60  # Cache for 1 hour


# === Create a global Oracle connection pool ===
print("Creating Oracle connection pool...")
dsn = oracledb.makedsn("20.84.145.157", 1521, service_name="XEPDB1")
print(f"Using DSN: {dsn}")
try:
    pool = oracledb.SessionPool(
        user="SHRIRAM",
        password="Admin123",
        dsn=dsn,
        min=2,
        max=10,
        increment=1,
        threaded=True,
        getmode=oracledb.SPOOL_ATTRVAL_WAIT
    )
except Exception as e:
    print(f"❌ Failed to create Oracle connection pool: {e}")
    exit(1)

print("Pool created successfully.")

# Close pool gracefully when app stops
atexit.register(lambda: pool.close())

# === Acquire a connection for each request ===

@app.before_request
def before_request():
    try:
        print("Acquiring database connection...")
        g.db = pool.acquire()
    except Exception as e:
        g.db = None
        print(f"❌ Error acquiring connection: {e}")

@app.teardown_request
def teardown_request(exception):
    db_conn = g.pop('db', None)
    if db_conn:
        try:
            pool.release(db_conn)
            print("✅ DB connection released.")
        except Exception as e:
            print(f"❌ Error releasing DB connection: {e}")


# === Error handler (500 and DB errors) ===
@app.errorhandler(Exception)
def handle_exception(e):
    print(f"❌ Unexpected error: {e}")
    return jsonify({"error": str(e)}), 500


def get_cities():
    print("Fetching cities from the database...")
    global cached_data_cities, last_refresh_cities
    current_time = time.time()
    if cached_data_cities is not None and (current_time - last_refresh_cities) < CACHE_TTL_SECONDS:
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
        last_refresh_cities = time.time()
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
    print("Fetching cities data...")
    cities = get_cities()
    return jsonify(cities)


@app.route("/railways")
def get_railways():
    global cached_data_railways, last_refresh_railways

    current_time = time.time()
    if cached_data_railways is not None and (current_time - last_refresh_railways) < CACHE_TTL_SECONDS:
        print("🔁 Returning cached railways data.")
        return Response(cached_data_railways, mimetype='application/x-ndjson')

    @stream_with_context
    def generate():
        global cached_data_railways, last_refresh_railways

        print("🚂 Starting to stream railways data...")
        ndjson_stream = StringIO()

        if not g.get("db"):
            yield json.dumps({"error": "Database connection failed"}) + "\n"
            return

        chunk_size = 200
        offset = 0
        done = False

        try:
            while not done:
                print(f"📦 Fetching rows {offset + 1} to {offset + chunk_size}...")

                cursor = g.db.cursor()
                cursor.execute("""
                    SELECT id, featurecla, part, continent, wkt_column
                    FROM (
                        SELECT id, featurecla, part, continent, wkt_column,
                               ROW_NUMBER() OVER (ORDER BY id) AS rn
                        FROM (
                            SELECT * FROM railways
                            WHERE wkt_column IS NOT NULL
                            ORDER BY DBMS_RANDOM.VALUE
                        )
                        WHERE ROWNUM <= 1000
                    )
                    WHERE rn BETWEEN :start_row AND :end_row
                """, start_row=offset + 1, end_row=offset + chunk_size)

                rows = cursor.fetchall()
                cursor.close()

                if not rows:
                    done = True
                    break

                chunk_features = []
                for row in rows:
                    try:
                        if row[4] is None:
                            continue
                        geom_wkt = row[4].read() if hasattr(row[4], 'read') else str(row[4])
                        geom = wkt.loads(geom_wkt).simplify(0.01)

                        feature = {
                            "type": "Feature",
                            "geometry": mapping(geom),
                            "properties": {
                                "id": row[0],
                                "featurecla": row[1],
                                "part": row[2],
                                "continent": row[3]
                            }
                        }
                        chunk_features.append(feature)
                    except Exception as e:
                        print(f"❌ Error processing row: {e}")
                        continue

                if chunk_features:
                    line = json.dumps({
                        "type": "FeatureCollection",
                        "features": chunk_features,
                        "chunk": offset // chunk_size + 1
                    }) + "\n"
                    ndjson_stream.write(line)
                    yield line

                offset += chunk_size
                if len(rows) < chunk_size:
                    done = True

        except Exception as e:
            print(f"❌ Stream error: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

        # Cache the output
        cached_data_railways = ndjson_stream.getvalue()
        last_refresh_railways = time.time()
        print("✅ Cached /railways NDJSON stream")

    return Response(generate(), mimetype='application/x-ndjson')


if __name__ == "__main__":
    app.run(debug=True)

