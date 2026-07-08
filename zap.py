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
TABLE_NAME = 'properties_poa_4_dorm_novo'

# DDL Statement - CORRIGIDO: removi a coluna duplicada 'rua'
TABLE_CREATION_QUERY = f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id SERIAL PRIMARY KEY,
    rua TEXT,
    preco TEXT,
    url TEXT,
    bairro TEXT,
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
    Scrape multiple Zap Imóveis pages — each in a new Firefox instance.
    Takes a screenshot of each page and collects listings.
    '''
    try:
        num_pages = int(input("Enter number of pages to scrape: "))
    except ValueError:
        num_pages = 1

    for page in range(1, num_pages + 1):
        print(f"\n🚀 Opening Firefox instance for page {page}...")

        # Create a new Firefox instance
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options

        options = Options()
        options.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
        options.add_argument("--disable-notifications")
        options.add_argument("--mute-audio")

        driver_local = webdriver.Firefox(options=options)

        # Compose the page URL
        url = (
            "https://www.zapimoveis.com.br/venda/apartamentos/rs+porto-alegre/3-quartos/"
            "?transacao=venda"
            "&tipos=apartamento_residencial"
            f"&pagina={page}"
            "&precoMaximo=800000"
            "&precoMinimo=200000"
        )
        
        # The full URL is:
        # https://www.zapimoveis.com.br/venda/apartamentos/rs+porto-alegre/3-quartos/?transacao=venda&tipos=apartamento_residencial&pagina=1&precoMaximo=700000&precoMinimo=200000

        # Open page and wait for it to load
        driver_local.get(url)
        time.sleep(3.5)

        # Take screenshot
        screenshot_path = f"zapimoveis_page_{page}.png"
        driver_local.save_screenshot(screenshot_path)
        print(f"🖼 Screenshot saved: {screenshot_path}")

        # Parse page
        soup = BeautifulSoup(driver_local.page_source, "lxml")
        items = soup.find_all("li", {"data-cy": "rp-property-cd"})
        print(f"🔍 Found {len(items)} properties on page {page}")

        for item in items:
            parse_item(item)

        # Close that instance
        driver_local.quit()
        print(f"✅ Closed Firefox for page {page}")

    print(f"\n🎯 Finished scraping {num_pages} page(s). Total items: {len(json_list)}")



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
    while total_scrolled < 50000:
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
    try:
        # The property data is inside an <a> tag within the <li>
        link_tag = property_item.find('a')
        if not link_tag:
            return False

        # Extract URL
        url = link_tag.get('href', '')
        if not url.startswith('http'):
            url = "https://www.zapimoveis.com.br" + url

        # Extract Title - look for h2 with location data
        title_tag = link_tag.find('h2', {'data-cy': 'rp-cardProperty-location-txt'})
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Extract Street (nome da rua)
        street_tag = link_tag.find('p', {'data-cy': 'rp-cardProperty-street-txt'})
        street = street_tag.get_text(strip=True) if street_tag else ''

        # Extract bairro information - CORRIGIDO: extrair do span dentro do h2
        bairro = ''
        if title_tag:
            # Primeiro tenta pegar o texto do span (descrição do imóvel)
            span_tag = title_tag.find('span')
            span_text = span_tag.get_text(strip=True) if span_tag else ''
            
            # O bairro e cidade estão no texto principal do h2 (após o span)
            # O formato é: "Bairro, Cidade"
            h2_text = title_tag.get_text()
            if span_tag:
                # Remove o texto do span do texto completo para ficar só com "Bairro, Cidade"
                h2_text = h2_text.replace(span_text, '').strip()
            
            if ',' in h2_text:
                parts = h2_text.split(',')
                bairro = parts[0].strip()  # Primeira parte é o bairro
            else:
                bairro = h2_text.strip()

        # Extract Price - look for price element
        price_tag = link_tag.find('p', class_=lambda x: x and 'text-2-25' in x and 'text-neutral-120' in x)
        if not price_tag:
            # Alternative approach for price
            price_div = link_tag.find('div', {'data-cy': 'rp-cardProperty-price-txt'})
            if price_div:
                price_tags = price_div.find_all('p')
                if price_tags:
                    price_tag = price_tags[0]  # Primeiro p é o preço
        price = price_tag.get_text(strip=True) if price_tag else ''

        # Extract additional costs (condominio, IPTU)
        costs_div = link_tag.find('div', {'data-cy': 'rp-cardProperty-price-txt'})
        additional_costs = ''
        if costs_div:
            costs_p_tags = costs_div.find_all('p')
            if len(costs_p_tags) > 1:
                additional_costs = costs_p_tags[1].get_text(strip=True)

        # Extract property features
        features = link_tag.find('ul', class_=lambda x: x and 'group/amenities-row' in x)
        
        area = ''
        n_dormitorios = ''
        n_banheiros = ''
        n_garagem = ''
        
        if features:
            # Area
            area_li = features.find('li', {'data-cy': 'rp-cardProperty-propertyArea-txt'})
            if area_li:
                area_text = area_li.get_text(strip=True)
                area_match = re.search(r'(\d+)\s*m²', area_text)
                area = area_match.group(1) if area_match else re.sub(r'[^\d]', '', area_text)
            
            # Bedrooms
            bedrooms_li = features.find('li', {'data-cy': 'rp-cardProperty-bedroomQuantity-txt'})
            if bedrooms_li:
                bedrooms_text = bedrooms_li.get_text(strip=True)
                n_dormitorios = re.sub(r'[^\d]', '', bedrooms_text)
            
            # Bathrooms
            bathrooms_li = features.find('li', {'data-cy': 'rp-cardProperty-bathroomQuantity-txt'})
            if bathrooms_li:
                bathrooms_text = bathrooms_li.get_text(strip=True)
                n_banheiros = re.sub(r'[^\d]', '', bathrooms_text)
            
            # Parking
            parking_li = features.find('li', {'data-cy': 'rp-cardProperty-parkingSpacesQuantity-txt'})
            if parking_li:
                parking_text = parking_li.get_text(strip=True)
                n_garagem = re.sub(r'[^\d]', '', parking_text)

        # Use additional costs as description for now
        description = additional_costs

        json_data = {
            'rua': street,
            'preco': price,
            'url': url,
            'bairro': bairro,
            'area': area,
            'n_dormitorios': n_dormitorios,
            'n_banheiros': n_banheiros,
            'n_garagem': n_garagem,
            'resumo': description
        }

        # Create JSON only if object is valid (if url is present)
        if url and url != "https://www.zapimoveis.com.br":
            add_json(json_data)
            return True
            
    except Exception as e:
        print(f"Error parsing item: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False


def add_json(json_data):
    '''
    Creates and appends a JSON object to the JSON List
    '''
    rua = json_data.get('rua', '')
    preco = json_data.get('preco', '')
    url = json_data.get('url', '')
    bairro = json_data.get('bairro', '')  # NOVO: bairro
    area = json_data.get('area', '')
    n_dormitorios = json_data.get('n_dormitorios', '')
    n_banheiros = json_data.get('n_banheiros', '')
    n_garagem = json_data.get('n_garagem', '')
    resumo = json_data.get('resumo', '')

    print("Rua: " + str(rua))
    print("Preco: " + str(preco))
    print("Url: " + url)
    print("Bairro: " + bairro)  # NOVO: bairro
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
        "bairro": bairro,  # NOVO: bairro
        "areaEmM2": area,
        "n_dormitorios": n_dormitorios,
        "n_banheiros": n_banheiros,
        "n_garagem": n_garagem,
        "resumo": resumo,
    }

    json_list.append(json_obj)

# --------------------------------------------------------------------------------------------------

json_list = []

# Adds the JSON objects to the JSON List
search_zap_imoveis()

# CORRIGIDO: A query INSERT estava com número incorreto de parâmetros
INSERT_QUERY = f'''
INSERT INTO {TABLE_NAME} (
rua,
preco,
url,
bairro,
areaEmM2,
n_dormitorios,
n_banheiros,
n_garagem,
resumo
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
'''

# Inserts the JSON objects into the database
for item in json_list:
    cur.execute(INSERT_QUERY, (
        item['rua'],
        item['preco'],
        item['url'],
        item['bairro'],  # NOVO: bairro
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