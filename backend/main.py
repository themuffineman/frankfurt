from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from keywords import pinterest_titles
import time
service = Service(executable_path='chromedriver.exe')
google_list_selector= "#rso"
results_a_tag_selector = "#rso > div > div > div > div.kb0PBd.A9Y9g.jGGQ5e > div > div > span > a"
pagination_selector = "#botstuff > div > div:nth-child(3) > table > tbody > tr"
pagination_item_selector = "#botstuff > div > div:nth-child(3) > table > tbody > tr > td > a"
app = Flask(__name__)
@app.route('/frank', methods=['GET'])
def frank():
    driver = None
    try:
        # Initialize driver with options
        options = Options()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        driver = webdriver.Chrome(service=service, options=options)
        
        # Get search keyword
        keyword = pinterest_titles.popleft()
        
        # Perform initial search
        driver.get('https://www.google.com/')
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "gLFyf")))
        input_element = driver.find_element(By.CLASS_NAME, "gLFyf")
        input_element.clear()
        input_element.send_keys(keyword + Keys.ENTER)
        
        # Wait for search results to load
        wait_for_elements(driver, [
            (By.CSS_SELECTOR, google_list_selector),
            (By.CSS_SELECTOR, pagination_selector)
        ], timeout=30)
        
        print("Found the list of results and pagination")
        
        # Get initial results
        results_hrefs = []
        collect_results(driver, results_hrefs)
        
        # Process pagination
        pagination_list = driver.find_element(By.CSS_SELECTOR, pagination_selector)
        pagination_items = [
            item.get_attribute("href")
            for item in pagination_list.find_elements(By.CSS_SELECTOR, pagination_item_selector)
            if item.get_attribute("href")
        ]
        
        # Navigate through pages and collect results
        for pagination_item in pagination_items:
            print(f"Navigating to next page:🫡")
            driver.get(pagination_item)
            
            # Wait for results to load
            wait_for_elements(driver, [(By.CSS_SELECTOR, google_list_selector)], timeout=30)
            
            # Collect results from this page
            collect_results(driver, results_hrefs)
            break
        
        return jsonify({"results": results_hrefs})
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    finally:
        if driver:
            driver.quit()


def wait_for_elements(driver, element_locators, timeout=30):
    """
    Wait for multiple elements to be present
    
    Args:
        driver: WebDriver instance
        element_locators: List of tuples (By, selector)
        timeout: Maximum wait time in seconds
    """
    for by, selector in element_locators:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )


def collect_results(driver, results_hrefs):
    """
    Collect all result links from the current page
    
    Args:
        driver: WebDriver instance
        results_hrefs: List to append results to
    """
    # Make sure results are loaded
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, results_a_tag_selector))
    )
    
    # Get result container
    results_list = driver.find_element(By.CSS_SELECTOR, google_list_selector)
    
    # Get all result links
    results = results_list.find_elements(By.CSS_SELECTOR, results_a_tag_selector)
    
    # Extract hrefs
    for result in results:
        href = result.get_attribute("href")
        if href:
            results_hrefs.append(href)
        


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)