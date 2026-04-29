def test_get_weather_success(monkeypatch):
    class DummyResponse:
        def __init__(self, data):
            self.data = data
        def json(self):
            return self.data

    def dummy_jsonify(data):
        return DummyResponse(data)

    monkeypatch.setattr("flask.jsonify", dummy_jsonify)

    response, status_code = get_weather()
    assert status_code == 200
    assert isinstance(response, DummyResponse)
    assert response.json() == [
        {"city": "New York", "temperature": 22, "condition": "Sunny"},
        {"city": "London", "temperature": 16, "condition": "Cloudy"},
        {"city": "Tokyo", "temperature": 25, "condition": "Rainy"},
        {"city": "Sydney", "temperature": 18, "condition": "Windy"}
    ]

def test_get_weather_exception(monkeypatch):
    def dummy_jsonify(data):
        raise Exception("fail")

    monkeypatch.setattr("flask.jsonify", dummy_jsonify)

    response, status_code = get_weather()
    assert status_code == 500
    assert response.get_json() == {"error": "Unable to fetch weather data"}