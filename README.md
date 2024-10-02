<h1 align="center">Zap Scraper - A Web Scraper Built with Python</h1>
<p align="center">
  <img src="scraper-logo.png" alt="Zap-Scraper-logo" width="120px" height="120px"/>
  <br>
  <i>This script is an example of a Web Scraper built in
    <br>Python.</i>
  <br>
</p>


[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/nothingnothings/zap-scraper)
[![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](https://github.com/nothingnothings/zap-scraper/blob/master/README.pt-br.md)

## Introduction




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
├── output_format_example.json
├── requirements.txt
├── scraped_page_example.html
├── scraper-logo.png
├── test.py
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

## Notes

- In the root of the project, there is an HTML file called `scraped_page_example.html` that shows the format of the page affected by the script's scraping.
- Also at the root of the project, there is the `output_format_example.json` file, which shows how each property from the page is inserted into the final SQL table `properties`.
- The script examines only one page at a time to avoid bot detection by the website. If you want to scan more than one page, change the value of the `url` variable in the `searchZapImoveis` function to the desired page.
  
Example:

```
# first page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=1

# second page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=2

```

