import requests

response = requests.post(
    "http://localhost:5173/api/auth/login",
    json={"email": "admin@kaoyan.com", "password": "123456"}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
