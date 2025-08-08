from playwright.sync_api import sync_playwright
import time

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://127.0.0.1:8080", timeout=10000)

            # Give the app time to load and for the button to be clickable
            copy_button = page.locator("#copy_btn_term")
            copy_button.wait_for(state="visible", timeout=5000)

            # Click the copy button and take a screenshot
            copy_button.click()
            time.sleep(1.5) # Wait for animation to be in progress
            page.screenshot(path="jules-scratch/verification/confetti_copy_button.png")

            # Click the model button and take a screenshot
            model_button = page.locator("#model_btn_term")
            model_button.wait_for(state="visible", timeout=5000)
            model_button.click()
            time.sleep(1.5) # Wait for animation to be in progress
            page.screenshot(path="jules-scratch/verification/confetti_model_button.png")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_test()
