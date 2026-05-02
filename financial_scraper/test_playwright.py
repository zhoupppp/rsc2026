from playwright.sync_api import sync_playwright
import time
import json

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Handle new pages (tabs)
        def on_page(new_page):
            print("New page opened:", new_page.url)
            new_page.on("response", handle_response)
            # Wait for it to load
            new_page.wait_for_load_state("networkidle")
            print("New page loaded completely")
            
        def handle_response(response):
            if "api/pof/person" in response.url and response.request.method == "POST":
                print(f"Intercepted API response: {response.url}, Status: {response.status}")
                print(f"Payload: {response.request.post_data}")
                try:
                    data = response.json()
                    print(f"Data snippet: {str(data)[:200]}")
                except Exception as e:
                    print("Error parsing json", e)
                    
        page.on("response", handle_response)
        
        print("Navigating to AMAC personOrgList.html...")
        page.goto("https://gs.amac.org.cn/amac-infodisc/res/pof/person/personOrgList.html", wait_until="networkidle")
        time.sleep(2)
        
        page.evaluate('''() => {
            $("#orgType").val("");
            $("#orgName").val("上海重阳投资管理股份有限公司");
            $(".search-btn").click();
        }''')
        
        time.sleep(3)
        html = page.evaluate('() => $("table tbody").html()')
        print(html)
        browser.close()

if __name__ == "__main__":
    run()