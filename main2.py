import requests

response = requests.post(
    "http://127.0.0.1:11434",
    json={"model": "llama3:latest", "prompt": "Hello!"}
)
print(response.json())