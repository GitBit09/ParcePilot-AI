import urllib.request, json, sys

def test_sse():
    url = "https://parcelpilot-backend-q1lr.onrender.com/chat/stream"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer token-northstar-001"
    }
    data = json.dumps({
        "messages": [{"role": "user", "content": "Show me all my recent orders"}]
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print("Status:", response.status)
            while True:
                line = response.readline()
                if not line:
                    break
                print("RECV:", line.decode("utf-8").strip())
    except urllib.error.HTTPError as e:
        print("HTTP ERROR:", e.code, e.read().decode("utf-8"))
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test_sse()
