#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 01:14:54 2024

@author: dakid
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from bs4 import BeautifulSoup
import time
import csv

def get_driver():
  """
  Creates and returns a single shared Firefox WebDriver instance.
  """
  firefox_options = Options()
  firefox_options.add_argument('-headless')
  firefox_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/100.0')
  geckodriver_path = 'driver/firefox/geckodriver'
  firefox_service = FirefoxService(geckodriver_path)
  return webdriver.Firefox(service=firefox_service, options=firefox_options)

# Function to get user input for scraping parameters
def get_user_input():
    product_id = input("🛍️ Enter AliExpress Product ID: ")
    woo_id = input("📦 Enter WooCommerce Product ID (this will be set as the value for product_id column in the CSV. Leave empty to use AliExpress Product ID): ")
    
    
    start_from_recent_input = input("🚀 Start from recent reviews? (yes/no): ").lower()
    start_from_recent = start_from_recent_input == 'yes'
    
    num_reviews_input = input("✨ Enter the number of reviews to scrape (or press Enter to scrape all): ")
    num_reviews = int(num_reviews_input) if num_reviews_input else None

    min_rating_input = input("🌟 Enter minimum stars rating to filter reviews (1 - 5 or press Enter for no filtering): ")
    min_rating = int(min_rating_input) if min_rating_input else None

    return product_id, woo_id, num_reviews, start_from_recent, min_rating


def get_html_content(driver, url, num_reviews):
    """
    Fetches the outerHTML of the reviews element from the given URL using the provided WebDriver.
    """
    driver.get(url)
    driver.implicitly_wait(10)  # Set a default implicit wait time

    # Execute JavaScript to click the button and load initial reviews
    button_script = 'document.querySelector("#root > div > div.pdp-body.pdp-wrap > div > div.pdp-body-top-left > div.comet-v2-anchor.navigation--wrap--RttKRTy.notranslate.navigation--is23--LHKnr7b > div > div > a.comet-v2-anchor-link.comet-v2-anchor-link-active").click();'
    driver.execute_script(button_script)

    # Execute JavaScript to click the "View More" button to load additional reviews
    view_more_button_script = 'return document.querySelector("#nav-review > div.ae-evaluation-list > div.ae-evaluation-view-more > button");'
    view_more_button = WebDriverWait(driver, 30).until(lambda driver: driver.execute_script(view_more_button_script))
    if view_more_button:
        view_more_button.click()

        # Execute JavaScript to wait for the presence of the reviews container
        reviews_container_script = 'return document.querySelector("#nav-review > div.ae-evaluation-list > div.ae-all-list-box");'
        WebDriverWait(driver, 30).until(lambda driver: driver.execute_script(reviews_container_script))

        # Execute JavaScript to wait for the presence of the reviews box within the container
        reviews_box_script = 'return document.querySelector("#nav-review > div.ae-evaluation-list > div.ae-all-list-box > div > div > div > div.ae-evaluateList-box");'
        WebDriverWait(driver, 30).until(lambda driver: driver.execute_script(reviews_box_script))

        # Simulate scrolling to dynamically load reviews
        for _ in range(num_reviews // 10):  # Assuming 10 reviews load with each scroll
            scroll_script = 'document.querySelector("#nav-review > div.ae-evaluation-list > div.ae-all-list-box").scrollTop += 500;'  # Adjust the scroll value as needed
            driver.execute_script(scroll_script)
            time.sleep(10)  # Adjust the sleep time based on the time it takes to load reviews

        # Execute JavaScript to get the full outerHTML of the reviews box
        reviews_outer_html_script = 'return document.querySelector("#nav-review > div.ae-evaluation-list > div.ae-all-list-box > div > div > div > div.ae-evaluateList-box").outerHTML;'
        reviews_outer_html = driver.execute_script(reviews_outer_html_script)

        return reviews_outer_html

    else:
        print("😬 View More reviews button not found on the product page.")
        return None

def parse_reviews(html_content):
    """
    Parses the HTML content and extracts review data using BeautifulSoup.
    """
    soup_html = BeautifulSoup(html_content, 'html.parser')

    reviews = []
    for review_element in soup_html.find_all('div', class_=None):  # Iterate over all div elements without a specific class

        p_review = review_element.find('div', class_='ae-evaluateList-card')
        p_score_e = p_review.find('div', class_='ae-evaluateList-card-header')
        p_score = p_score_e.find('div', class_='ae-stars-box')
        p_title_box = p_review.find('div', class_='ae-evaluateList-card-title-box')
        p_img = p_review.find('div', class_='ae-evaluateList-card-img-box')
        
        if not p_review:
            continue
        
        media_list = [img['src'] for img in p_img.find_all('img', class_='ae-evaluateList-card-img')] if p_img else None
        
        productId = woo_id if not None else product_id
        
        display_name = p_title_box.find('div', class_='ae-evaluateList-card-name').get_text(strip=True)
        
        display_name = 'Store Shopper' if display_name == 'AliExpress Shopper' else display_name

        
        review_data = {
            'review_content': p_review.find('div', class_='ae-evaluateList-card-content').get_text(strip=True),
            'review_score': len(p_score.find_all('img', class_='ae-stars')),
            'date': p_score_e.find('div', class_='ae-evaluateList-card-date').get_text(strip=True),
            'product_id': productId,
            'display_name': display_name,
            'email': None,
            'order_id': None,
            'media': media_list
        }

        # Filter reviews based on minimum rating
        if min_rating is None or review_data['review_score'] >= min_rating:
            reviews.append(review_data)

        # Break loop if the specified number of reviews is reached
        if num_reviews is not None and len(reviews) >= num_reviews:
            break

    return reviews

def save_to_csv(reviews, filename):
  with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['review_content', 'review_score', 'date', 'product_id', 'display_name', 'email', 'order_id', 'media']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(reviews)

def get_correct_url(product_id):
  """
  Returns the potentially redirected URL using the provided WebDriver.
  """
  base_url = 'https://www.aliexpress.com/item/'
  url = f'{base_url}{product_id}.html#nav-review'
  driver = get_driver()
  try:
    driver.get(url)
    driver.implicitly_wait(10)
    return driver.current_url
  finally:
    driver.quit()  # Close the driver after use
    
def get_reviews(product_id, woo_id, num_reviews=None, start_from_recent=True, min_rating=None):
    """
    Scrapes reviews for the given product ID and saves them to a CSV file.

    Args:
        product_id (str): The AliExpress product ID.
        woo_id (str): The WooCommerce product ID.
        num_reviews (int, optional): The number of reviews to scrape. Defaults to None (scrape all).
        start_from_recent (bool, optional): Whether to start scraping from recent reviews. Defaults to True.
        min_rating (int, optional): Minimum rating to filter reviews by. Defaults to None (no filtering).

    Returns:
        None: If no reviews are found, otherwise saves reviews to a CSV file.
    """
    
      
    driver = get_driver()
    print("🪄 Scraping started...")
    
    if woo_id is None:
        f_name = product_id
    else:
        f_name = woo_id
    
    try:
        url = get_correct_url(product_id)
        html_content = get_html_content(driver, url, num_reviews)
        reviews = parse_reviews(html_content)

        if reviews:
            csv_filename = f'reviews/{f_name}_reviews.csv'
            save_to_csv(reviews, csv_filename)
            print(f"\n🎉 Reviews scraped and saved to {csv_filename}")
        else:
            print("\n🥵 No reviews found.")

    finally:
        driver.quit()
        
# Get user input
product_id, woo_id, num_reviews, start_from_recent, min_rating = get_user_input()

# Run the scraping function
get_reviews(product_id, woo_id, num_reviews, start_from_recent, min_rating)
