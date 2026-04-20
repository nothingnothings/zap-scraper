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
from seleniumbase import SB

# Load environment variables from .env file
load_dotenv()


# Ignore warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


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
TABLE_NAME = 'properties_poa_4_dorm_novo_imovelweb'

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


from seleniumbase import SB
import random

def search_zap_imoveis():
    '''
    Scrape multiple pages using ONE SeleniumBase session
    (avoids Cloudflare blocking)
    '''
    try:
        num_pages = int(input("Enter number of pages to scrape: "))
    except ValueError:
        num_pages = 1

    min_bed = 3
    max_bed = 4
    num_garage = 2
    min_price = 200000
    max_price = 800000

    # ✅ ONE browser session only
    with SB(browser="chrome", headless=False, uc=True) as sb:

        for page in range(1, num_pages + 1):
            print(f"\n🚀 Opening page {page}...")

            url = (
                f"https://www.imovelweb.com.br/"
                f"apartamentos-venda-porto-alegre-rs-"
                f"desde-{min_bed}-ate-{max_bed}-quartos-"
                f"mais-de-{num_garage}-vagas-"
                f"{min_price}-{max_price}-reales"
                f"-pagina-{page}.html"
            )

            sb.open(url)

            # wait for page to load
            sb.wait_for_element("body", timeout=15)

            # ✅ human-like delay
            sb.sleep(random.uniform(2.5, 5.5))

            # ✅ simulate user behavior
            sb.scroll_to_bottom()
            sb.sleep(random.uniform(1.0, 2.5))
            sb.scroll_to_top()
            sb.sleep(random.uniform(1.0, 2.0))

            html = sb.get_page_source()

            # 🚫 detect Cloudflare block
            if "Just a moment" in html or "cf-challenge" in html:
                print("🚫 Blocked by Cloudflare! Stopping...")
                break

            soup = BeautifulSoup(html, "lxml")

            # ⚠️ adjust selector if needed
            items = soup.find_all("div", {"data-qa": "posting PROPERTY"})

            print(f"🔍 Found {len(items)} properties on page {page}")

            # 🚫 if suddenly zero → likely block
            if len(items) == 0:
                print("⚠️ No items found — possible block or end of results")
                break

            for item in items:
                parse_item(item)

            print(f"✅ Finished page {page}")

            # ✅ delay between pages (VERY important)
            sb.sleep(random.uniform(3.0, 7.0))

    print(f"\n🎯 Finished scraping. Total items: {len(json_list)}")



def return_selenium_soup(url):
    with SB(browser="firefox", headless=True) as sb:
        sb.open(url)
        sb.wait_for_element("body", timeout=10)
        return BeautifulSoup(sb.get_page_source(), "lxml")



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
    Parses and extracts data from a single ImovelWeb property card.
    '''
    try:
        # Extract URL - from data-to-posting attribute
        url_path = property_item.get('data-to-posting', '')
        if url_path:
            url = "https://www.imovelweb.com.br" + url_path
        else:
            # Fallback: try to find the link in the description
            desc_link = property_item.find('a', href=True)
            url = desc_link.get('href', '') if desc_link else ''
            if url and not url.startswith('http'):
                url = "https://www.imovelweb.com.br" + url

        # Extract Price
        price_tag = property_item.find('h2', {'data-qa': 'POSTING_CARD_PRICE'})
        price = price_tag.get_text(strip=True) if price_tag else ''

        # Extract Condominium fee (optional - can be used as resumo or separate field)
        condominio_tag = property_item.find('h2', {'data-qa': 'expensas'})
        condominio = condominio_tag.get_text(strip=True) if condominio_tag else ''

        # Extract Features (area, bedrooms, bathrooms, parking)
        features_tag = property_item.find('h3', {'data-qa': 'POSTING_CARD_FEATURES'})
        
        area = ''
        n_dormitorios = ''
        n_banheiros = ''
        n_garagem = ''
        
        if features_tag:
            feature_spans = features_tag.find_all('span', class_='postingMainFeatures-module__posting-main-features-span')
            for span in feature_spans:
                text = span.get_text(strip=True)
                if 'm²' in text:
                    # Extract area (e.g., "235 m² tot." or "82 m² tot.")
                    area_match = re.search(r'(\d+)\s*m²', text)
                    area = area_match.group(1) if area_match else ''
                elif 'quartos' in text:
                    # Extract bedrooms (e.g., "3 quartos")
                    bedrooms_match = re.search(r'(\d+)\s*quartos', text)
                    n_dormitorios = bedrooms_match.group(1) if bedrooms_match else ''
                elif 'ban' in text:
                    # Extract bathrooms (e.g., "3 ban.")
                    bathroom_match = re.search(r'(\d+)\s*ban', text)
                    n_banheiros = bathroom_match.group(1) if bathroom_match else ''
                elif 'vagas' in text:
                    # Extract parking spaces (e.g., "2 vagas")
                    parking_match = re.search(r'(\d+)\s*vagas', text)
                    n_garagem = parking_match.group(1) if parking_match else ''

        # Extract Address and Neighborhood
        address_tag = property_item.find('h4', class_='postingLocations-module__location-address-in-listing')
        location_tag = property_item.find('h4', {'data-qa': 'POSTING_CARD_LOCATION'})
        
        rua = ''
        bairro = ''
        
        if address_tag:
            address_text = address_tag.get_text(strip=True)
            # Extract street name (remove number and neighborhood if present)
            # Format examples: "Rua Landel de Moura, 710 - Tristeza" or just "Rua Marina Sirângelo Castello"
            if ' - ' in address_text:
                parts = address_text.split(' - ')
                rua = parts[0].strip()
                # The part after '-' is sometimes the neighborhood, but we'll get bairro from location_tag
            else:
                rua = address_text
        
        if location_tag:
            location_text = location_tag.get_text(strip=True)
            # Format: "Tristeza, Porto Alegre" or "Jardim Itu Sabará, Porto Alegre"
            if ',' in location_text:
                bairro = location_text.split(',')[0].strip()
            else:
                bairro = location_text

        # Extract Description
        desc_tag = property_item.find('h2', {'data-qa': 'POSTING_CARD_DESCRIPTION'})
        if desc_tag:
            desc_link = desc_tag.find('a')
            description = desc_link.get_text(strip=True) if desc_link else desc_tag.get_text(strip=True)
        else:
            description = ''

        # Use condominium fee as resumo (or combine with description)
        resumo = condominio if condominio else description[:200] if description else ''

        # Build the data dictionary
        json_data = {
            'rua': rua,
            'preco': price,
            'url': url,
            'bairro': bairro,
            'area': area,
            'n_dormitorios': n_dormitorios,
            'n_banheiros': n_banheiros,
            'n_garagem': n_garagem,
            'resumo': resumo
        }

        # Only add if we have a valid URL
        if url and url != "https://www.imovelweb.com.br":
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