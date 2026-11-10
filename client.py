import requests

url = "http://127.0.0.1:8000/chat"

response=requests.post(
    url=url,
    json={"question":"什么是tool calling"},
    timeout=60
)
response.raise_for_status()
data=response.json()
print("状态码：", response.status_code)
print("响应内容：", response.text)
print(data["answer"])