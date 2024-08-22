#!/usr/bin/env python
# coding: utf-8


"""
This script scrapes real estate data from Zap Imóveis, processes it, 
and inserts it into a containerized MySQL database.

Dependencies:
- pymysql
- BeautifulSoup
- selenium
"""


# Standard library imports
import random
import re
import time
import warnings
import os
from dotenv import load_dotenv

# Third-party library imports
import pymysql
from pymysql.err import OperationalError, ProgrammingError
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

# Load environment variables from .env file
load_dotenv()

# Retrieve the proxy URL from the environment variable
proxy_url = os.getenv('PROXY_URL')

# Ignore warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Proxy configuration
proxy = {
    "http": proxy_url
}

# Set up Firefox browser options
options = Options()
options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'
options.add_argument("--disable-notifications")
options.add_argument("--mute-audio")
options.add_argument(f"--proxy-server={proxy}")

# Assign options to Firefox driver
driver = webdriver.Firefox(options=options)

# Database Parameters
db_params = {
    'user': 'myuser',
    'password': 'mypassword',
    'host': 'localhost',  # or '127.0.0.1' if you have trouble with 'localhost'
    'port': 3306,         # MySQL default port
    'database': 'mydatabase'
}

# Connect to the database
conn = pymysql.connect(**db_params)

# Create a cursor object
cur = conn.cursor()

# Desired Table
TABLE_NAME = 'properties'

# DDL Statement
TABLE_CREATION_QUERY = f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id SERIAL PRIMARY KEY,
    regiao TEXT,
    preco TEXT,
    url TEXT,
    rua TEXT,
    regiaoCidade TEXT,
    areaEmM2 TEXT,
    n_dormitorios TEXT,
    n_banheiros TEXT,
    n_garagem TEXT,
    resumo TEXT
);
'''

# Table Helper Function:
def table_exists(cursor, table_name):
    '''
    Check if the table exists
    '''

    query = f"""
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_name = '{table_name}'
    );
    """
    cursor.execute(query)
    return cursor.fetchone()[0]

# Create the 'properties' table if it does not exist
try:
    if table_exists(cur, TABLE_NAME):
        print(f"Table '{TABLE_NAME}' already exists.")
    else:
        cur.execute(TABLE_CREATION_QUERY)
        conn.commit()
        print(f"Table '{TABLE_NAME}' created successfully.")
except OperationalError as e:
    print(f"Operational error occurred: {e}")
except ProgrammingError as e:
    print(f"Programming error occurred: {e}")


# --------------------------------------------------------------------------------------------------
#
# Functions:


def search_zap_imoveis():
    '''
    Scrape real estate data from Zap Imóveis
    '''

    # Only a single page is loaded, to avoid the site's bot countermeasures
    for x in range(1, 2):
        print("Zap Imoveis - page", x)

        # Load initial page
        url = "https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/4-quartos/"
        soup = return_selenium_soup(url, 2.5)

        # Scroll page down, to load more items (page has infinite scroll loading mechanism)
        scroll_down()

        # Load page content after the scrolling
        result = driver.page_source
        soup = BeautifulSoup(result, 'lxml')

        # Find all relevant items on the page
        items = soup.findAll("div", { "class": re.compile(r"ListingCard_result-card__")})

        # Parse each item, creating a JSON object for each one
        for soup_item in items:
            parse_item(soup_item)



def return_selenium_soup(url, time_await):
    '''
    Return BeautifulSoup object for a given URL 
    '''

    driver.get(url)
    time.sleep(time_await)
    result = driver.page_source
    soup = BeautifulSoup(result, 'lxml')
    return soup



def scroll_down(min_scroll_amount=1000,
                max_scroll_amount=1200,
                click_button=False,
                x_path_btn="",
                min_sleep=2.0,
                max_sleep=3.0):
    ''' 
    Scrolls down the page, so more items are loaded.
    '''

    total_scrolled = 0

    # 160000 is a fair amount
    while total_scrolled < 200000: 
        # Calculate the next scroll amount
        scroll_amount = random.randint(min_scroll_amount, max_scroll_amount)

        # Scroll down by the calculated amount
        driver.execute_script("window.scrollBy(0, window.innerHeight / 5);")

        # Update the total scrolled amount
        total_scrolled += scroll_amount

        # Optional: Click a button if specified
        if click_button:
            button_click(x_path_btn)

        # Sleep for a random time to mimic human-like behavior
        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)

        print(
            "Scrolled down by " + str(scroll_amount) + " pixels. " +
            "Total scrolled: " + str(total_scrolled) + " pixels. " +
            "Carregando mais dados..."
        )


def button_click(xpath):
    '''
    Click a button identified by its XPath.
    '''

    ent_to_click = driver.find_element(By.XPATH, xpath)
    driver.execute_script("arguments[0].click();", ent_to_click)



def parse_item(property_item):
    '''
    Parses and extracts data from a single item.
    '''

    # Extract Title
    title_tag = property_item.find('h2', {'data-cy': 'rp-cardProperty-location-txt'})
    title = title_tag.get_text(strip=True) if title_tag else ''

    # Extract Price
    price_tag = property_item.find(
    'p',
    {
        'class': (
            'l-text l-u-color-neutral-28 l-text--variant-heading-small '
            'l-text--weight-bold undefined'
        )
    })

    print(price_tag)
    price = price_tag.get_text(strip=True) if price_tag else ''

    # Extract URL
    url_tag = property_item.find('a', {'itemprop': 'url'})
    url = url_tag['href'] if url_tag else ''

    # Extract Region and City
    region_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-street-txt'})
    regiao = region_tag.get_text(strip=True) if region_tag else ''
    regiao_cidade = regiao.split(',')[1].strip() if ',' in regiao else '---'

    # Extract Additional Information
    area_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-propertyArea-txt'})
    area = area_tag.get_text(strip=True) if area_tag else ''

    rooms_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-bedroomQuantity-txt'})
    n_dormitorios = rooms_tag.get_text(strip=True) if rooms_tag else ''

    bathrooms_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-bathroomQuantity-txt'})
    n_banheiros = bathrooms_tag.get_text(strip=True) if bathrooms_tag else ''

    parking_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-parkingSpacesQuantity-txt'})
    n_garagem = parking_tag.get_text(strip=True) if parking_tag else ''

    # Extract Description (resumo)
    description_tag = property_item.find('p', {'data-cy': 'rp-cardProperty-description-txt'})
    description = description_tag.get_text(strip=True) if description_tag else ''

    json_data = {
        'rua': title,
        'preco': price,
        'url': url,
        'regiao': regiao,
        'regiao_cidade': regiao_cidade,
        'area': area,
        'n_dormitorios': n_dormitorios,
        'n_banheiros': n_banheiros,
        'n_garagem': n_garagem,
        'resumo' : description
    }

    # Create JSON only if object is valid (if url is present)
    if url:
        add_json(json_data)


def add_json(json_data):
    '''
    Creates and appends a JSON object to the JSON List
    '''

    rua = json_data.get('rua')
    preco = json_data.get('preco')
    url = json_data.get('url')
    regiao = json_data.get('regiao')
    regiao_cidade = json_data.get('regiao_cidade')
    area = json_data.get('area')
    n_dormitorios = json_data.get('n_dormitorios')
    n_banheiros = json_data.get('n_banheiros')
    n_garagem = json_data.get('n_garagem')
    resumo = json_data.get('resumo')

    print("Rua: " + str(rua))
    print("Preco: " + str(preco))
    print("Url: " +  url)
    print("Regiao: " + regiao)
    print("Regiao da Cidade: " + regiao_cidade)
    print("Área em m2: " + area)
    print("Número de dormitórios: " + str(n_dormitorios))
    print("Número de banheiros: " + str(n_banheiros))
    print("Número de garagens: " + str(n_garagem))
    print("Resumo: " + resumo)
    print("----")

    json_obj = {
    "rua": rua,
    "preco": preco,
    "url": url,
    "regiao": regiao,
    "regiao_cidade": regiao_cidade, 
    "areaEmM2": area.replace('m²', ''),
    "n_dormitorios": n_dormitorios,
    "n_banheiros": n_banheiros,
    "n_garagem": n_garagem,
    "resumo" : resumo,
    }

    json_list.append(json_obj)

# --------------------------------------------------------------------------------------------------

json_list = []

# Adds the JSON objects to the JSON List
search_zap_imoveis()

INSERT_QUERY = f'''
INSERT INTO {TABLE_NAME} (
rua,
preco,
url,
regiao,
regiaoCidade,
areaEmM2,
n_dormitorios,
n_banheiros,
n_garagem,
resumo
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
'''
# Inserts the JSON objects into the database
for item in json_list:
    cur.execute(INSERT_QUERY, (
        item['regiao'],
        item['preco'],
        item['url'],
        item['rua'],
        item['regiao_cidade'],
        item['areaEmM2'],
        item['n_dormitorios'],
        item['n_banheiros'],
        item['n_garagem'],
        item['resumo']
    ))

# Commits the transaction
conn.commit()

# Closes the database connection
cur.close()
conn.close()

print(f"Data successfully inserted into {TABLE_NAME} table.")
