from playwright.sync_api import sync_playwright
html = "<html><body><h1>PDF test</h1></body></html>"
out = "test_playwright.pdf"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html, wait_until="networkidle")
    page.pdf(path=out, format="A4")
    browser.close()
print("wrote", out)