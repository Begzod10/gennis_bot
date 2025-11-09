import os
import requests
import json

TOKEN = os.getenv("GENNIS_TOKEN",
                  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2MjAxMjgwMiwianRpIjoiODI4YjI0OTEtNmQwOC00N2Y1LWFjZGUtYjkzYmEyYWQ1ZWEyIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjhkMDI3NzJjNTE5MzExZjBhNTQ4MzFkODQyNzBhMjIwIiwibmJmIjoxNzYyMDEyODAyLCJjc3JmIjoiMzU4NmM5OWYtNjY2ZS00Yjk2LTljYTgtZmE2YTBkOGNmOTVjIiwiZXhwIjoxNzYyMDk5MjAyfQ.NRA2lZU3d0ZTTUH6Vcn5bID0sRsCLZoIaw4onv202Fw")

TEST_LIST_URL = "https://classroom.gennis.uz/api/pisa/student/get/list"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "User-Agent": "MyScript/1.0"
}


def get_tests():
    try:
        response = requests.get(TEST_LIST_URL, headers=headers)
        print("Status:", response.status_code)
        print("Response text:", response.text[:300])
        if response.status_code == 401:
            print("❌ Token yemad")
            return []
        if response.status_code != 200:
            print("⚠️ Server yemad", response.status_code)
            return []
        data = response.json()
        if isinstance(data, list):
            return [
                {"id": item["id"], "name": item["name"]}
                for item in data if "id" in item and "name" in item
            ]
        else:
            print("⚠️ Format yemad", type(data))
    except Exception as e:
        print("⚠️ Test yemad", e)
    return []


def mark_test_finished(test_id: int):
    try:
        url = f"https://classroom.gennis.uz/api/pisa/student/finish/{test_id}"
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            print(f"✅ Test {test_id} belgilandi (finished=True)")
            return True
        else:
            print(f"⚠️ Test {test_id} ni yakunlashda xatolik: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print("⚠️ Testni yakunlashin yemad:", e)
        return False
