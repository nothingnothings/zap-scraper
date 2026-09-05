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
    'host': 'localhost',
    'port': 3306,
    'database': 'mydatabase'
}

# Connect to the database
conn = pymysql.connect(**db_params)

# Create a cursor object
cur = conn.cursor()

# Desired Table
TABLE_NAME = 'properties_poa_4_dorm_teste'


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
    IPTU TEXT,
    condominio TEXT
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


def parse_additional_costs(resumo):
    """
    Separates the resumo field into IPTU and condominio.

    Examples:
        "IPTU R$ 1.200 | Condomínio R$ 203"
            -> ("R$ 1.200", "R$ 203")

        "IPTU R$ 100"
            -> ("R$ 100", "")

        "Condomínio R$ 700"
            -> ("", "R$ 700")

        ""
            -> ("", "")
    """

    iptu = ""
    condominio = ""

    if not resumo:
        return iptu, condominio

    parts = resumo.split("|")

    for part in parts:
        part = part.strip()

        if re.search(r"\bIPTU\b", part, re.IGNORECASE):
            value = re.sub(
                r"^\s*IPTU\s*",
                "",
                part,
                flags=re.IGNORECASE
            ).strip()

            iptu = value

        elif re.search(r"\bCondom[ií]nio\b", part, re.IGNORECASE):
            value = re.sub(
                r"^\s*Condom[ií]nio\s*",
                "",
                part,
                flags=re.IGNORECASE
            ).strip()

            condominio = value

    return iptu, condominio


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
    """
    Scrape multiple OLX pages.
    Each page is opened in a new Firefox instance.
    """

    try:
        num_pages = int(input("Enter number of pages to scrape: "))
    except ValueError:
        num_pages = 1

    for page in range(1, num_pages + 1):

        print(f"\n🚀 Opening Firefox instance for page {page}...")

        # Create a new Firefox instance
        options = Options()
        options.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
        options.add_argument("--disable-notifications")
        options.add_argument("--mute-audio")

        driver_local = webdriver.Firefox(options=options)

        # Compose OLX URL
        url = (
            "https://www.olx.com.br/imoveis/venda/estado-rs/"
            "regioes-de-porto-alegre-torres-e-santa-cruz-do-sul"
            "?ps=600000"
            "&pe=1200000"
            "&ipe=3000"
            "&bas=2"
            "&gsp=2"
            "&ss=125"
            "&se=250"
            "&ros=3"
            "&ros=4"
            f"&o={page}"
        )

        print(f"🌐 URL: {url}")

        # Open page
        driver_local.get(url)

        # Wait for page to load
        time.sleep(5)

        # Take screenshot
        screenshot_path = f"olx_page_{page}.png"
        driver_local.save_screenshot(screenshot_path)

        print(f"🖼 Screenshot saved: {screenshot_path}")

        # Parse page
        soup = BeautifulSoup(
            driver_local.page_source,
            "lxml"
        )

        # OLX property cards
        items = soup.select("section.olx-adcard")

        print(
            f"🔍 Found {len(items)} properties on page {page}"
        )

        for item in items:
            parse_item(item)

        # Close Firefox
        driver_local.quit()

        print(f"✅ Closed Firefox for page {page}")

    print(
        f"\n🎯 Finished scraping {num_pages} page(s). "
        f"Total items: {len(json_list)}"
    )


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
    """
    Parses a single OLX property card.
    """

    try:

        # ---------------------------------------------------------
        # URL
        # ---------------------------------------------------------

        link_tag = property_item.find(
            "a",
            {"data-testid": "adcard-link"}
        )

        if not link_tag:
            return False

        url = link_tag.get("href", "").strip()

        if not url:
            return False

        # OLX URLs are already absolute
        if not url.startswith("http"):
            url = "https://www.olx.com.br" + url


        # ---------------------------------------------------------
        # TITLE
        # ---------------------------------------------------------

        title_tag = property_item.find(
            "h2",
            class_=lambda x: x and "olx-adcard__title" in x
        )

        title = (
            title_tag.get_text(strip=True)
            if title_tag
            else ""
        )


        # ---------------------------------------------------------
        # STREET
        # ---------------------------------------------------------

        # The supplied OLX HTML does not contain the street.
        # Therefore, leave it empty rather than guessing from
        # the property title.

        street = ""


        # ---------------------------------------------------------
        # LOCATION / BAIRRO
        # ---------------------------------------------------------

        location_tag = property_item.find(
            "p",
            class_=lambda x: x and "olx-adcard__location" in x
        )

        location = (
            location_tag.get_text(" ", strip=True)
            if location_tag
            else ""
        )

        bairro = ""

        if location:

            # Example:
            # "Porto Alegre, Jardim Sabará"
            #
            # or:
            # "Gravataí, Loteamento Jardim Timbaúva"

            parts = [
                part.strip()
                for part in location.split(",")
            ]

            if len(parts) >= 2:
                bairro = parts[-1]
            else:
                bairro = parts[0]


        # ---------------------------------------------------------
        # PRICE
        # ---------------------------------------------------------

        price_tag = property_item.find(
            "h3",
            class_=lambda x: x and "olx-adcard__price" in x
        )

        price = (
            price_tag.get_text(strip=True)
            if price_tag
            else ""
        )


        # ---------------------------------------------------------
        # ADDITIONAL COSTS
        # ---------------------------------------------------------

        additional_costs = []

        price_info_tags = property_item.select(
            '[data-testid="adcard-price-info"]'
        )

        for tag in price_info_tags:

            cost = tag.get_text(" ", strip=True)

            if cost:
                additional_costs.append(cost)

        description = " | ".join(additional_costs)


        # ---------------------------------------------------------
        # PROPERTY FEATURES
        # ---------------------------------------------------------

        area = ""
        n_dormitorios = ""
        n_banheiros = ""
        n_garagem = ""


        # OLX puts the information in aria-label.
        #
        # Examples from HTML:
        #
        # aria-label="208 metros quadrados"
        # aria-label="3 quartos"
        # aria-label="2 banheiros"
        # aria-label="2 vagas de garagem"

        detail_tags = property_item.select(
            "div.olx-adcard__detail"
        )


        for detail in detail_tags:

            aria_label = detail.get("aria-label", "").strip()

            if not aria_label:
                continue


            # Area
            if "metros quadrados" in aria_label.lower():

                match = re.search(
                    r"([\d.,]+)\s*metros quadrados",
                    aria_label,
                    re.IGNORECASE
                )

                if match:
                    area = (
                        match.group(1)
                        .replace(".", "")
                        .replace(",", ".")
                    )


            # Bedrooms
            elif "quartos" in aria_label.lower():

                match = re.search(
                    r"(\d+)\s*quartos?",
                    aria_label,
                    re.IGNORECASE
                )

                if match:
                    n_dormitorios = match.group(1)


            # Bathrooms
            elif "banheiros" in aria_label.lower():

                match = re.search(
                    r"(\d+)\s*banheiros?",
                    aria_label,
                    re.IGNORECASE
                )

                if match:
                    n_banheiros = match.group(1)


            # Parking
            elif "vagas de garagem" in aria_label.lower():

                match = re.search(
                    r"(\d+)\s*vagas?\s*de\s*garagem",
                    aria_label,
                    re.IGNORECASE
                )

                if match:
                    n_garagem = match.group(1)


        # ---------------------------------------------------------
        # DATA
        # ---------------------------------------------------------

        json_data = {
            "rua": street,
            "preco": price,
            "url": url,
            "bairro": bairro,
            "area": area,
            "n_dormitorios": n_dormitorios,
            "n_banheiros": n_banheiros,
            "n_garagem": n_garagem,
            "resumo": description,
        }


        # ---------------------------------------------------------
        # ADD TO JSON LIST
        # ---------------------------------------------------------

        add_json(json_data)

        return True


    except Exception as e:

        print(f"❌ Error parsing OLX item: {e}")

        import traceback
        traceback.print_exc()

        return False


def add_json(json_data):
    '''
    Creates and appends a JSON object to the JSON List
    '''

    rua = json_data.get('rua', '')
    preco = json_data.get('preco', '')
    url = json_data.get('url', '')
    bairro = json_data.get('bairro', '')
    area = json_data.get('area', '')
    n_dormitorios = json_data.get('n_dormitorios', '')
    n_banheiros = json_data.get('n_banheiros', '')
    n_garagem = json_data.get('n_garagem', '')
    resumo = json_data.get('resumo', '')

    # Split resumo into IPTU and condominio
    iptu, condominio = parse_additional_costs(resumo)

    print("Rua: " + str(rua))
    print("Preco: " + str(preco))
    print("Url: " + url)
    print("Bairro: " + bairro)
    print("Área em m2: " + area)
    print("Número de dormitórios: " + str(n_dormitorios))
    print("Número de banheiros: " + str(n_banheiros))
    print("Número de garagens: " + str(n_garagem))
    print("IPTU: " + iptu)
    print("Condomínio: " + condominio)
    print("----")

    json_obj = {
        "rua": rua,
        "preco": preco,
        "url": url,
        "bairro": bairro,
        "areaEmM2": area,
        "n_dormitorios": n_dormitorios,
        "n_banheiros": n_banheiros,
        "n_garagem": n_garagem,
        "IPTU": iptu,
        "condominio": condominio,
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
    IPTU,
    condominio
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
'''


# Inserts the JSON objects into the database
for item in json_list:
    cur.execute(INSERT_QUERY, (
        item['rua'],
        item['preco'],
        item['url'],
        item['bairro'],
        item['areaEmM2'],
        item['n_dormitorios'],
        item['n_banheiros'],
        item['n_garagem'],
        item['IPTU'],
        item['condominio']
    ))

# Commits the transaction
conn.commit()

# Closes the database connection
cur.close()
conn.close()

print(f"Data successfully inserted into {TABLE_NAME} table.")