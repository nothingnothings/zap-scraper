<h1 align="center">Zap Scraper - A Web Scraper Built with Python</h1>
<p align="center">
  <img src="scraper-logo.png" alt="Zap-Scraper-logo" width="120px" height="120px"/>
  <br>
  <i>This script is an example of a Web Scraper built in
    <br>Python.</i>
  <br>
</p>




## Introduction

[![en](https://img.shields.io/badge/lang-en-red.svg?style=flat-square)](https://github.com/nothingnothings/zap-scraper)
[![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg?style=flat-square)](https://github.com/nothingnothings/zap-scraper/blob/master/README.pt-br.md)

This Python script extracts and stores information about listings available on the Zap Imóveis website in a containerized SQL database.


The script uses Selenium for web scraping and BeautifulSoup for the parsing of the HTML.


For more information about how to use it, read the instructions below.




## Project's Directory Structure


```
.\
│
├── docker\
│   └── docker-compose.yml
│
├── .env
├── .env.example
├── .gitignore
├── README.md
├── db_config.py
├── gui.py
├── output_format_example.json
├── requirements.txt
├── scraped_page_example.html
├── scraper-logo.png
├── test.py
├── test_gui_logic.py
└── zap.py
```

## Requirements.txt

```
pymysql
requests
beautifulsoup4
selenium
python-dotenv
```

## Installation/Usage 

1. Run `git clone` to clone the project into your local Git repository.

2. Create a free account on [ZenRows](https://www.zenrows.com/) to obtain a proxy. After creating the account, copy the proxy URL found at `https://app.zenrows.com/builder`, just below the API key.

3. Insert the proxy URL (e.g., `http://<YOUR_API_KEY>:@proxy.zenrows.com:8001`) received from ZenRows into the `.env` file at the root of the project. To do this, rename the `.env.example` file to `.env` and add the proxy URL in this format:
```
PROXY_URL=<YOUR_PROXY_URL>
```
4. Install the correct version of [geckodriver](https://github.com/mozilla/geckodriver/releases) for your operating system. Download and install the appropriate version (Linux, Mac, Windows) to ensure the script works correctly.

5. The `docker-compose.yml` file contains a ready-to-use SQL database. To initialize it, with Docker installed and running, type the following commands:

```
cd docker
docker-compose up -d
```

6. Install the necessary dependencies listed in the `requirements.txt` file using `pip`:

```
pip install -r requirements.txt
```

7. Before running the main script `zap.py`, it is recommended to run the test script `test.py`, which opens a Google page to ensure everything is working correctly:

```
python test.py
```

## GUI Dashboard

The project includes a desktop dashboard (`gui.py`) built with Tkinter (bundled with
Python) that lets you browse the scraped records, view "recommended apartment"
categories, and inspect aggregate metrics — all without touching SQL.

Features:

- **Browse any scraped table** — pick it from the dropdown and hit *Atualizar*.
- **Recommended categories** — All listings, Best value (price/m²), Largest
  apartments, Most rooms (bedrooms), Cheapest listings, Most garages/parking,
  and Most expensive/luxury.
- **Live metrics panel** — for the selected category it shows average price per m²,
  average price, average area (m²), average bedrooms, average bathrooms, and
  average garages.
- **Sortable columns** — click any table header to sort by that column; click it
  again to reverse the direction. Numeric columns (prices, areas, counts, ID) are
  sorted by value, and the active header shows the current direction.
- **Open a listing** — double-click any row to open its page on Zap Imóveis in
  your web browser.

To launch it:

```sh
python gui.py
```

If you'd like to check that the dashboard's data logic (number parsing, category
filtering, and metrics) is working without starting MySQL, run the offline test:

```sh
python test_gui_logic.py
```

The GUI reads its database credentials from the same `.env` file the scraper uses
(see `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env.example`),
so make sure the database container is running:

```sh
cd docker
docker-compose up -d
```

## Notes

- In the root of the project, there is an HTML file called `scraped_page_example.html` that shows the format of the page affected by the script's scraping.
- Also at the root of the project, there is the `output_format_example.json` file, which shows how each property from the page is inserted into the final SQL table `properties`.
- The script has a Zap Imóveis and a Imovel Web version. Choose whichever suits your needs (the Imovel Web version has a cloudflare verification bypass, needed to access the site's contents).
  
Example:

```
# first page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=1

# second page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=2

```

