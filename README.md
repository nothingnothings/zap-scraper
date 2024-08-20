<h1 align="center">Zap Scraper - Um Web Scraper Construído em Python</h1>
<p align="center">
  <img src="scraper-logo.png" alt="Zap-Scraper-logo" width="120px" height="120px"/>
  <br>
  <i>Este script é um exemplo de Web Scraper construído em
    <br>Python.</i>
  <br>
</p>




## Introdução




Script construído em Python que extrai e armazena informações sobre os anúncios disponibilizados no site Zap Imóveis em um banco de dados SQL containerizado. O Script emprega Selenium para o web scraping, e BeautifulSoup para o parse do HTML. Para mais informações sobre sua utilização, leia as instruções abaixo.




## Estrutura de Diretórios do Projeto


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


pymysql
requests
beautifulsoup4
selenium
python-dotenv
