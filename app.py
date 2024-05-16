from flask import Flask, jsonify, request
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from bs4 import BeautifulSoup
import re
import atexit
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from logging.handlers import RotatingFileHandler
import urllib.parse
from groq import Groq
from datetime import datetime
import time


def rewrite_sentence(sentence):
    api_key = "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"
    client = Groq(api_key=api_key)
    prompt = f"Rewrite the following sentence while maintaining the original length and immediately return the new sentence without any additional text or comments: '{sentence}'"
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama3-8b-8192",
    )
    rewritten_sentence = chat_completion.choices[0].message.content
    rewritten_sentence = rewritten_sentence.replace('"', '').replace("'", "")
    return rewritten_sentence

app = Flask(__name__)
if not app.debug:
    file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('Application startup')

client = MongoClient("mongodb+srv://logoman:abcd1234@cluster0.om1oelb.mongodb.net/?retryWrites=true&w=majority")
db = client['deals_database']
women_deals_collection = db['women_deals']
men_deals_collection = db['men_deals']
deals_collection = db['deals']


def scheduled_scrape():
    men_url = 'https://www.dealmoon.com/en/clothing-jewelry-bags/mens-clothing'
    women_url = 'https://www.dealmoon.com/en/clothing-jewelry-bags/womens-clothing'

    print("fetching men")
    men_deals = scrape_deals(men_url, men_deals_collection, max_items=100)
    print("fetching women")
    women_deals = scrape_deals(women_url, women_deals_collection, max_items=100)
    deals_collection.delete_many({})
    deals_collection.insert_many(men_deals)
    deals_collection.insert_many(women_deals)
    print("All deals scraped and saved successfully")

#
# scheduler = BackgroundScheduler()
# scheduler.add_job(func=scheduled_scrape, trigger='interval', hours=12)
# scheduler.start()
#
# atexit.register(lambda: scheduler.shutdown())


@app.route('/get-women-deals', methods=['GET'])
def get_women_deals():
    deals = list(women_deals_collection.find({}, {'_id': 0}))
    return jsonify(deals)


@app.route('/get-men-deals', methods=['GET'])
def get_men_deals():
    deals = list(men_deals_collection.find({}, {'_id': 0}))
    return jsonify(deals)

@app.route('/get-all-deals', methods=['GET'])
def get_all_deals():
    deals = list(deals_collection.find({}, {'_id': 0}))
    return jsonify(deals)


def scrape_deals(url, collection, max_items=100):

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    headers = {
        'User-Agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    driver = Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(3)
    scraped_items = []
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        while len(scraped_items) < max_items:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            deals_list = soup.find('body').find('section', id='dealsList')
            mlist_divs = deals_list.find_all('div', class_='mlist v2', limit=max_items - len(scraped_items))

            for mlist in mlist_divs:
                p_left = mlist.find('div', class_='p-left')
                shop_now_link = p_left.find('a', class_='btn-buy')['href']
                try:
                    response = requests.get(shop_now_link, headers=headers, allow_redirects=True, timeout=30)
                    final_url = response.url
                except requests.RequestException as e:
                    print(f"Failed to follow redirects for {shop_now_link}: {str(e)}")
                    final_url = shop_now_link

                parsed_url = urllib.parse.urlparse(final_url)
                cleaned_url = urllib.parse.urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
                p_right = mlist.find('div', class_='p-right')
                title_link = p_right.find('a', class_='zoom-title')['href']

                detail_response = requests.get(title_link, headers=headers)
                time.sleep(1)
                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')

                title = detail_soup.find('h1', class_='title').get_text(strip=True)
                subtitle = detail_soup.find('div', class_='subtitle').get_text(strip=True)
                details_ul = detail_soup.select_one('div.mbody .minfor ul')
                details = []
                if details_ul:
                    for li in details_ul.find_all('li'):
                        text = li.get_text(strip=True)

                        text = re.sub(r'(code)(\d+)', r'\1 \2', text)
                        text = re.sub(r'(\D)(\d)', r'\1 \2', text)


                        text = re.sub(r'(\d)([A-Z][a-z])', r'\1 \2', text)
                        text = re.sub(r'(\d)([A-Z][A-Z])', r'\1 \2', text)

                        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

                        text = re.sub(r'\.([^\s])', r'. \1', text)

                        text = re.sub(r'\s{2,}', ' ', text)

                        text = re.sub(r'(?i)(code)(next|\w*)\s*((?:\w+\s*)*)',
                                        lambda m: m.group(1) + ' ' + m.group(2) + ''.join(m.group(3).split()), text)
                        rewrite = rewrite_sentence(text)
                        details.append(rewrite)
                        time.sleep(2)
                deal_info = {
                    'shop_now_link': cleaned_url,
                    'title_link': title_link,
                    'title': title,
                    'subtitle': subtitle,
                    'details': details,
                    'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                print(deal_info)
                scraped_items.append(deal_info)

                if len(scraped_items) >= max_items:
                    break
    finally:
        driver.quit()
    if scraped_items:
        collection.delete_many({})
        collection.insert_many(scraped_items)

    return scraped_items


@app.route('/deals-by-domain-women', methods=['POST'])
def get_deals_by_domain_women():
    data = request.get_json()
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain parameter is missing'}), 400

    deals = list(women_deals_collection.find({'shop_now_link': {'$regex': domain}}, {'_id': 0}))

    if not deals:
        return jsonify({'message': 'No deals found for the specified domain'}), 404

    return jsonify(deals)


@app.route('/deals-by-domain-men', methods=['POST'])
def get_deals_by_domain_men():
    data = request.get_json()
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain parameter is missing'}), 400

    deals = list(men_deals_collection.find({'shop_now_link': {'$regex': domain}}, {'_id': 0}))

    if not deals:
        return jsonify({'message': 'No deals found for the specified domain'}), 404

    return jsonify(deals)

@app.route('/deals-by-domain', methods=['POST'])
def get_deals_by_domain():
    data = request.get_json()
    domain = data.get('domain')

    if not domain:
        return jsonify({'error': 'Domain parameter is missing'}), 400

    # Fetch women's deals
    women_deals = list(women_deals_collection.find({'shop_now_link': {'$regex': domain}}, {'_id': 0}))

    # Fetch men's deals
    men_deals = list(men_deals_collection.find({'shop_now_link': {'$regex': domain}}, {'_id': 0}))

    if not women_deals and not men_deals:
        return jsonify({'message': 'No deals found for the specified domain'}), 404

    return jsonify({'women_deals': women_deals, 'men_deals': men_deals})


@app.route('/clean-urls', methods=['POST'])
def clean_urls():
    collections = [women_deals_collection, men_deals_collection]
    for collection in collections:
        deals = list(collection.find({}))
        for deal in deals:
            original_url = deal.get('shop_now_link', '')
            parsed_url = urllib.parse.urlparse(original_url)
            cleaned_url = urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
            collection.update_one({'_id': deal['_id']}, {'$set': {'shop_now_link': cleaned_url}})
    return jsonify({'message': 'URLs cleaned successfully'}), 200

@app.route('/manual-scrape', methods=['GET'])
def manual_scrape():
    try:
        scheduled_scrape()
        return jsonify({'message': 'Scraping triggered manually and data saved successfully'}), 200
    except Exception as e:
        app.logger.error(f"Failed to scrape: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/scrape', methods=['GET'])
def test_scrape():
    url = request.args.get('url', 'https://www.dealmoon.com/en/clothing-jewelry-bags/mens-clothing')
    max_items = int(request.args.get('max_items', 30))
    deals = scrape_deals(url, max_items)
    clean_deals = []
    for deal in deals:
        deal['_id'] = str(deal['_id'])
        clean_deals.append(deal)

    return jsonify(clean_deals)

@app.route('/edit-deals', methods=['POST'])
def edit_deals():
    try:
        deals = list(men_deals_collection.find({}))
        for deal in deals:
            updated_details = []
            for detail in deal['details']:
                detail = re.sub(r'(?i)(code)(next|\w*)\s*((?:\w+\s*)*)',
                            lambda m: m.group(1) + ' ' + m.group(2) + ''.join(m.group(3).split()), detail)
                updated_details.append(detail)
            print(updated_details)
            men_deals_collection.update_one(
                {'_id': deal['_id']},
                {'$set': {'details': updated_details}}
            )

        return jsonify({'message': 'Deals updated successfully'}), 200
    except Exception as e:
        app.logger.error(f"Failed to edit deals: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5004)


