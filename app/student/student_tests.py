import os
import requests
import json

# TOKEN = os.getenv("GENNIS_TOKEN",
#                   "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2NDE2MTEyNCwianRpIjoiNmY1YWFjNjEtMDJlYi00MDMyLWEwYTctZjVjY2MwNDAzZTE2IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImE5MWY5MDM0NzFjZDExZjBhMTM4ZmZkN2Q5ODFjMjdmIiwibmJmIjoxNzY0MTYxMTI0LCJjc3JmIjoiNjBjMjkxMTMtNGI3Yy00MzAyLTgxZTItY2EzZGNlNmI2Nzk1IiwiZXhwIjoxNzY0MjQ3NTI0fQ.achdcb7llpPidqZuF5bhblfqJVF9hUcKBwlVnhnb8qE")
primary_key = 9796
TEST_LIST_URL = f"https://classroom.gennis.uz/api/pisa/student/get/list_bot/{primary_key}"


# headers = {
#     "Authorization": f"Bearer {TOKEN}",
#     "Accept": "application/json",
#     "User-Agent": "MyScript/1.0"
# }


def get_tests():
    try:
        response = requests.get(TEST_LIST_URL)  # headers=headers
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
