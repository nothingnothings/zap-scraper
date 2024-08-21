#!/usr/bin/env python
# coding: utf-8

"""
This script scrapes real estate data from Zap Imóveis, processes it, 
and inserts it into a containerized MySQL database.

Dependencies:
- pandas
- pymysql
- numpy
- requests
- BeautifulSoup
- selenium
- openpyxl
"""

# Standard library imports
import json
import random
import re
import time
from datetime import date
import warnings
from difflib import SequenceMatcher
from urllib.request import urlopen as uReq
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the proxy URL from the environment variable
proxy_url = os.getenv('PROXY_URL')

# Third-party library imports
import pymysql
import requests
from bs4 import BeautifulSoup 
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

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
    
# DDL Statement
table_creation_query = '''
CREATE TABLE IF NOT EXISTS properties (
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
# Create the 'properties' table if it does not exist
cur.execute(table_creation_query)
print("Table created or already exists.")


# --------------------------------------------------------------------------------------------------
#
# Functions:


# Scrape real estate data from Zap Imóveis
def searchZapImoveis(pages = 2):
    # Only a single page is loaded, to avoid the site's bot countermeasures
    for x in range(1, 2):
        print("Zap Imoveis - page", x)

        # Load initial page
        url = "https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/4-quartos/"
        soup = returnSeleniumSoup(url, 2.5)

        # Scroll page down, to load more items (page has infinite scroll loading mechanism)
        scrollDown()
        
        # Load page content after the scrolling
        result = driver.page_source
        soup = BeautifulSoup(result, 'lxml')

        # Find all relevant items on the page
        itens = soup.findAll("div", { "class": re.compile(r"ListingCard_result-card__")})

        # Parse each item, creating a JSON object for each one
        for item in itens:
            parse_item(item)
            

# Return BeautifulSoup object for a given URL 
def returnSeleniumSoup(url, timeAwait):
    driver.get(url)
    time.sleep(timeAwait)
    result = driver.page_source
    soup = BeautifulSoup(result, 'lxml')
    return soup


# Scrolls down the page, so more items are loaded
def scrollDown(minScrollAmount=1000, maxScrollAmount=1200, maxTotalScroll=2000, clickButton=False, xPathBtn="", minSleep=2.0, maxSleep=3.0):
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    totalScrolled = 0
    
    # 160000 is a fair amount
    while totalScrolled < 200000: 
        # Calculate the next scroll amount
        scrollAmount = random.randint(minScrollAmount, maxScrollAmount)
        
        # Scroll down by the calculated amount
        driver.execute_script(f"window.scrollBy(0, window.innerHeight / 5);")
        
        # Update the total scrolled amount
        totalScrolled += scrollAmount
        
        # Optional: Click a button if specified
        if clickButton:
            buttonClick(xPathBtn)
        
        # Sleep for a random time to mimic human-like behavior
        sleepTime = random.uniform(minSleep, maxSleep)
        time.sleep(sleepTime)
        
        print(f"Scrolled down by {scrollAmount} pixels. Total scrolled: {totalScrolled} pixels. Carregando mais dados...")


# Click a button identified by its XPath.
def buttonClick(xpath):
    entToClick = driver.find_element_by_xpath(xpath)
    driver.execute_script("arguments[0].click();", entToClick)


# Parse and extract data from a single item.
def parse_item(item):
    # Extract URL
    url_tag = item.find('a', {'itemprop': 'url'})
    url = url_tag['href'] if url_tag else ''
    
    # Extract Price
    price_tag = item.find('p', {'class': 'l-text l-u-color-neutral-28 l-text--variant-heading-small l-text--weight-bold undefined'})
    print(price_tag)
    price = price_tag.get_text(strip=True) if price_tag else ''

    # Extract Title
    title_tag = item.find('h2', {'data-cy': 'rp-cardProperty-location-txt'})
    title = title_tag.get_text(strip=True) if title_tag else ''
    
    # Extract Region and City
    region_tag = item.find('p', {'data-cy': 'rp-cardProperty-street-txt'})
    regiao = region_tag.get_text(strip=True) if region_tag else ''
    regiaoCidade = regiao.split(',')[1].strip() if ',' in regiao else '---'

    # Extract Description
    description_tag = item.find('p', {'data-cy': 'rp-cardProperty-description-txt'})
    description = description_tag.get_text(strip=True) if description_tag else ''

    # Extract Additional Information
    area_tag = item.find('p', {'data-cy': 'rp-cardProperty-propertyArea-txt'})
    area = area_tag.get_text(strip=True) if area_tag else ''

    rooms_tag = item.find('p', {'data-cy': 'rp-cardProperty-bedroomQuantity-txt'})
    n_dormitorios = rooms_tag.get_text(strip=True) if rooms_tag else ''

    bathrooms_tag = item.find('p', {'data-cy': 'rp-cardProperty-bathroomQuantity-txt'})
    n_banheiros = bathrooms_tag.get_text(strip=True) if bathrooms_tag else ''

    parking_tag = item.find('p', {'data-cy': 'rp-cardProperty-parkingSpacesQuantity-txt'})
    n_garagem = parking_tag.get_text(strip=True) if parking_tag else ''

    # Create JSON only if object is valid (if url is present)
    if url:
        addJSON(title, price, url, regiao, regiaoCidade, area, n_dormitorios, n_banheiros, n_garagem, description)
    

def addJSON(rua, preco, url, regiao, regiaoCidade, area, n_dormitorios, n_banheiros, n_garagem, resumo):
    # Create and append a JSON object to the JSON List
    print("Rua: " + str(rua))
    print("Preco: " + str(preco))
    print("Url: " +  url)
    print("Regiao: " + regiao)
    print("Regiao da Cidade: " + regiaoCidade)
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
    "regiaoCidade": regiaoCidade, 
    "areaEmM2": area.replace('m²', ''),
    "n_dormitorios": n_dormitorios,
    "n_banheiros": n_banheiros,
    "n_garagem": n_garagem,
    "resumo" : resumo,
    }
    
    jsonList.append(json_obj)

# --------------------------------------------------------------------------------------------------

jsonList = []

# Adds the JSON objects to the JSON List
searchZapImoveis(pages = 2)

insert_query = '''
INSERT INTO properties (rua, preco, url, regiao, regiaoCidade, areaEmM2, n_dormitorios, n_banheiros, n_garagem, resumo)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
'''
# Inserts the JSON objects into the database
for item in jsonList:
    cur.execute(insert_query, (
        item['regiao'], 
        item['preco'], 
        item['url'], 
        item['rua'], 
        item['regiaoCidade'], 
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

print("Data inserted successfully into PostgreSQL table.")

