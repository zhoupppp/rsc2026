import urllib.request
import json
import urllib.error

# To test this, you must run the server first:
# uvicorn main:app --reload

def test_chat_filter():
    url = "http://127.0.0.1:8000/api/chat/filter"
    payload = {
        "messages": [
            {"role": "user", "content": "I want to find a fund manager in Beijing who works in 新能源"}
        ]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    
    print("Sending request to:", url)
    print("Payload:", json.dumps(payload, indent=2, ensure_ascii=False))
    print("---")
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode("utf-8")
            result = json.loads(resp_body)
            print("Response Code:", response.status)
            print("Response Body:", json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("type") == "search":
                print("✅ Successfully parsed as search!")
            elif result.get("type") == "clarify":
                print("✅ Successfully parsed as clarify!")
            else:
                print("❌ Unknown response type.")
                
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code)
        print("Error Body:", e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print("URL Error:", e.reason)
        print("Make sure the FastAPI server is running (uvicorn main:app --reload)")
    except Exception as e:
        print("Unexpected Error:", str(e))

if __name__ == "__main__":
    test_chat_filter()