GENNIS_TOKEN = os.getenv(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2Mjg1NjY4NCwianRpIjoiYmFhZTczZTAtNmU4Yy00NDU1LWEwYTktNGU4NjYzMzhiNjY5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjhkMDI3NzJjNTE5MzExZjBhNTQ4MzFkODQyNzBhMjIwIiwibmJmIjoxNzYyODU2Njg0LCJjc3JmIjoiZmY2OGFkZDktNGEyOS00OGZiLWFmMzEtMDFjZDliNmE2ZGVhIiwiZXhwIjoxNzYyOTQzMDg0fQ.kyqMRFUS8AcPDqMJ8yLD0duqw0Q0wwiGgGgAkcfdKlc")
TEST_LIST_URL = "https://classroom.gennis.uz/api/pisa/test/crud/34"
active_questions = {}
HEADERS = lambda token: {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "GennisBot/1.0"
}
