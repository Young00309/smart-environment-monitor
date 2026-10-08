from sense_emu import SenseHat  
import sqlite3
from datetime import datetime
import time
import os

sense = SenseHat()
DATABASE = os.getenv('ENV_MONITOR_DB', os.path.join(os.path.dirname(__file__), 'environment.db'))
ALERT_COLORS = {
    'temperature': (255, 0, 0),    
    'humidity': (0, 0, 255),       
    'pressure': (0, 255, 0)        
}
def get_calibrated_temperature():
    # Read CPU temperature (only real hardware needs to be calibrated)
    raw_temp = sense.get_temperature()
    return raw_temp
def collect_and_store_data():
    try:
        # Reading sensor data (calibrated temperature)
        temperature = get_calibrated_temperature()  
        humidity = sense.get_humidity()
        pressure = sense.get_pressure()

        
        print(f"[Calibration] Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%, Barometric pressure: {pressure:.1f}hPa")

      # Write to the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_data (timestamp, temperature, humidity, pressure)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), temperature, humidity, pressure))
        conn.commit()
        conn.close()

      # Check the threshold and trigger an alarm
        check_thresholds_and_alert(temperature, humidity, pressure)

    except Exception as e:
        print(f"Error: {e}")

def check_thresholds_and_alert(temperature, humidity, pressure):
    
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM settings WHERE id = 1')
        settings = cursor.fetchone()
        conn.close()

        alerts = []
        if temperature < settings['min_temp'] or temperature > settings['max_temp']:
            alerts.append('temperature')
        if humidity < settings['min_humidity'] or humidity > settings['max_humidity']:
            alerts.append('humidity')
        if pressure < settings['min_pressure'] or pressure > settings['max_pressure']:
            alerts.append('pressure')

        sense.clear()

        if alerts:
            print(f"[!] Alerts detected: {', '.join(alerts)}")
            for _ in range(3):  # Each alarm flashes 3 times
                for alert_type in alerts:
                    color = ALERT_COLORS[alert_type]
                    sense.show_message(
                        f"{alert_type.upper()} ALERT!",
                        text_colour=color,
                        back_colour=(30, 30, 30),  
                        scroll_speed=0.05
                    )
                    sense.clear()
                    time.sleep(0.3)
    except Exception as e:
        print(f"Alarm System Error: {e}")

while True:
    collect_and_store_data()
    time.sleep(3)
