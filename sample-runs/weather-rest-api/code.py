from flask import Flask, jsonify

app = Flask(__name__)

dummy_weather_data = [
    {"city": "New York", "temperature": 22, "condition": "Sunny"},
    {"city": "London", "temperature": 16, "condition": "Cloudy"},
    {"city": "Tokyo", "temperature": 25, "condition": "Rainy"},
    {"city": "Sydney", "temperature": 18, "condition": "Windy"}
]

@app.route('/weather', methods=['GET'])
def get_weather():
    try:
        return jsonify(dummy_weather_data), 200
    except Exception:
        return jsonify({"error": "Unable to fetch weather data"}), 500

if __name__ == '__main__':
    app.run(debug=True)