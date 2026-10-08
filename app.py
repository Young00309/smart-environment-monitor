from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
from scipy.stats import linregress
import numpy as np
import os
from flask import jsonify
from flask import Flask, jsonify

app = Flask(__name__)
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error, please try again later'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Interface not found'}), 404
# Create a Flask app instance
app = Flask(__name__)
CORS(app) # Cross-origin requests are allowed

# Database path
DATABASE = os.getenv('ENV_MONITOR_DB', os.path.join(os.path.dirname(__file__), 'environment.db'))

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_settings_table():
    print("[DEBUG] creating settings table...")
    conn = sqlite3.connect(DATABASE)  
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            min_temp FLOAT DEFAULT 0,
            max_temp FLOAT DEFAULT 40,
            min_humidity FLOAT DEFAULT 10,
            max_humidity FLOAT DEFAULT 90,
            min_pressure FLOAT DEFAULT 970,
            max_pressure FLOAT DEFAULT 1030
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO settings (id) VALUES (1)')
    conn.commit()
    conn.close()
    print("The [DEBUG] settings table has been created!")

init_settings_table()  # Call the initialization function
# Root path routing
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current')
def get_current_data():
             

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # ------------ Step 1: Get the latest sensor data ------------
        cursor.execute('''
            SELECT timestamp, temperature, humidity, pressure 
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        sensor_data = cursor.fetchone()
        
        if not sensor_data:
            return jsonify({"error": "Sensor data not found"}), 404
        
       # ------------ Step 2: Get the threshold set by the user ------------
        cursor.execute('SELECT * FROM settings WHERE id = 1')
        settings = cursor.fetchone()
        if not settings:
            return jsonify({"error": "Threshold configuration not found"}), 404
        
        # ------------ Step 3: Check if the data exceeds the threshold ------------
        alerts = []
        temperature = sensor_data['temperature']
        humidity = sensor_data['humidity']
        pressure = sensor_data['pressure']
        
        if temperature < settings['min_temp'] or temperature > settings['max_temp']:
            alerts.append('temperature')
        
        if humidity < settings['min_humidity'] or humidity > settings['max_humidity']:
            alerts.append('humidity')
        
        if pressure < settings['min_pressure'] or pressure > settings['max_pressure']:
            alerts.append('pressure')
        
      # ------------ Returned Result (with Warnings) ------------
        return jsonify({
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "timestamp": sensor_data['timestamp'],
            "alerts": alerts  
        })
        
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
    finally:
        conn.close()  

@app.route('/api/history')
def get_history_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        SELECT timestamp, temperature 
        FROM sensor_data 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    ''', (start_str, end_str))
    data = cursor.fetchall()
    conn.close()
    
    # Handle empty data cases
    if not data:
        return jsonify([])
    
    history = [{'time': row['timestamp'], 'value': row['temperature']} for row in data]
    return jsonify(history)

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        # Update thresholds
        conn.execute('''
            UPDATE settings SET
                min_temp = ?,
                max_temp = ?,
                min_humidity = ?,
                max_humidity = ?,
                min_pressure = ?,
                max_pressure = ?
            WHERE id = 1
        ''', (
            data['min_temp'], data['max_temp'],
            data['min_humidity'], data['max_humidity'],
            data['min_pressure'], data['max_pressure']
        ))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    else:
       # Get the current threshold
        cursor = conn.execute('SELECT * FROM settings WHERE id = 1')
        settings = cursor.fetchone()
        conn.close()
        return jsonify({
            'min_temp': settings['min_temp'],
            'max_temp': settings['max_temp'],
            'min_humidity': settings['min_humidity'],
            'max_humidity': settings['max_humidity'],
            'min_pressure': settings['min_pressure'],
            'max_pressure': settings['max_pressure']
        })

@app.route('/api/analysis')
def temperature_analysis():
    conn = get_db_connection()
    cursor = conn.cursor()
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=6)  # Analyze past 6 hours
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        SELECT timestamp, temperature FROM sensor_data 
        WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC
    ''', (start_str, end_str))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows or len(rows) < 2:
        return jsonify({"error": "Not enough data for analysis"}), 400

    times = [datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S") for row in rows]
    temps = [row['temperature'] for row in rows]

    # Convert timestamps to numeric values (e.g., minutes since start)
    base_time = times[0]
    x = [(t - base_time).total_seconds() / 60.0 for t in times]  # in minutes

    # Sudden spike/drop detection
    spikes = []
    for i in range(1, len(temps)):
        if abs(temps[i] - temps[i-1]) > 3.0:
            spikes.append({"time": times[i].strftime("%Y-%m-%d %H:%M:%S"), "delta": temps[i] - temps[i-1]})

    # Trend detection using linear regression
    slope, intercept, r_value, p_value, std_err = linregress(x, temps)
    trend = "upward" if slope > 0.05 else "downward" if slope < -0.05 else "stable"

    # Prediction (e.g., 1 hour later)
    predicted_temp = slope * (x[-1] + 60) + intercept

    # Predict when the temperature will exceed the max and min thresholds
    settings = get_thresholds()  # Get the current threshold settings
    max_temp = settings['max_temp']
    min_temp = settings['min_temp']

    # Calculate when the temperature will exceed the thresholds based on the trend line
    time_to_max = None
    time_to_min = None

    if slope > 0:  # Rising temperature trend
        # Solve for time when temperature will exceed max_temp
        time_to_max = (max_temp - intercept) / slope
        # Solve for time when temperature will fall below min_temp
        time_to_min = (min_temp - intercept) / slope
    elif slope < 0:  # Falling temperature trend
        # Solve for time when temperature will fall below min_temp
        time_to_min = (min_temp - intercept) / slope
        # Solve for time when temperature will exceed max_temp
        time_to_max = (max_temp - intercept) / slope

    # Convert the predicted times to a readable format
    time_to_max = base_time + timedelta(minutes=time_to_max) if time_to_max else None
    time_to_min = base_time + timedelta(minutes=time_to_min) if time_to_min else None

    return jsonify({
        "spikes": spikes,
        "trend": trend,
        "predicted_temp": round(predicted_temp, 2),
        "current_temp": temps[-1],
        "slope": slope,
        "time_to_max": time_to_max.strftime("%Y-%m-%d %H:%M:%S") if time_to_max else None,
        "time_to_min": time_to_min.strftime("%Y-%m-%d %H:%M:%S") if time_to_min else None
    })

def get_thresholds():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings WHERE id = 1')
    settings = cursor.fetchone()
    conn.close()
    return settings


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
