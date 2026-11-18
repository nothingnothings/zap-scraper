<h1 align="center">Zap Scraper - Um Web Scraper Construído em Python</h1>
<p align="center">
  <img src="scraper-logo.png" alt="Zap-Scraper-logo" width="120px" height="120px"/>
  <br>
  <i>Este script é um exemplo de Web Scraper construído em
    <br>Python.</i>
  <br>
</p>




## Introdução

[![en](https://img.shields.io/badge/lang-en-red.svg?style=flat-square)](https://github.com/nothingnothings/zap-scraper)
[![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg?style=flat-square)](https://github.com/nothingnothings/zap-scraper/blob/master/README.pt-br.md)

Script construído em Python que extrai e armazena informações sobre os anúncios disponibilizados no site Zap Imóveis em um banco de dados SQL containerizado. 

O Script emprega Selenium para o web scraping, e BeautifulSoup para o parse do HTML. 

Para mais informações sobre sua utilização, leia as instruções abaixo.




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

## Instalação/Utilização 

1. Rode `git clone` para clonar o projeto dentro de seu repositório local Git

2. Crie uma conta gratuita no site [ZenRows](https://www.zenrows.com/) para obter um proxy. Após a criação da conta, copie a URL de proxy vista em `https://app.zenrows.com/builder`, logo abaixo da API key

3. Insira a URL do proxy (e.g `http://<SUA_API_KEY>:@proxy.zenrows.com:8001`), recebida no ZenRows, no arquivo .env na raiz do projeto. Para isso, renomeie o arquivo `.env.example` para `.env` e adicione a URL do proxy, neste formato:
```
PROXY_URL=<SUA_URL_DE_PROXY>
```
4. Instale a versão correta do [geckodriver](https://github.com/mozilla/geckodriver/releases) para o seu sistema operacional. Baixe e instale a versão adequada (Linux, Mac, Windows) para garantir que o script funcione corretamente

5. O arquivo docker-compose.yml contém uma base de dados SQL pronta para uso. Para inicializá-la, com o Docker instalado e rodando, digite os seguinte comandos: 
```
cd docker
docker-compose up -d
```

6. Instale as dependências necessárias listadas no arquivo `requirements.txt` usando o `pip`:

```
pip install -r requirements.txt
```

7. Antes de executar o script principal `zap.py`, é recomendável rodar o script de teste `test.py`, o qual abre uma página do Google para garantir que tudo está funcionando corretamente:

```
python test.py
```

## Painel Gráfico (GUI)

O projeto inclui um painel gráfico de desktop para consultar os dados gravados
pelo scraper. Para abri-lo:

```sh
python gui.py
```

Recursos do painel:

- **Escolha a tabela** — selecione qualquer tabela raspada no menu suspenso e
  clique em *Atualizar*.
- **Categorias recomendadas** — Todas as listagens, Melhor custo-benefício
  (menor preço por m²), Maiores apartamentos, Mais quartos, Mais baratos,
  Mais garagens e Mais caros/luxo.
- **Métricas dinâmicas** — para a categoria selecionada são exibidos: preço
  médio por m², preço médio, área média (m²), média de quartos, média de
  banheiros e média de garagens.
- **Colunas ordenáveis** — clique no cabeçalho de uma coluna para ordenar por
  ela; clique novamente para inverter a direção. Colunas numéricas (preços,
  áreas, contagens e ID) são ordenadas pelo valor, e o cabeçalho ativo mostra
  a direção atual.
- **Abrir anúncio** — dê um duplo clique em uma linha para abrir a página do
  imóvel no Zap Imóveis no seu navegador.

Para conferir se a lógica do painel (parsing de números, filtro de categorias e
cálculo de métricas) está funcionando sem iniciar o MySQL, execute o teste offline:

```sh
python test_gui_logic.py
```

A interface lê as credenciais do banco a partir do mesmo arquivo `.env` usado
pelo scraper (veja `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` em
`.env.example`), portanto garanta que o container do banco esteja rodando:

```sh
cd docker
docker-compose up -d
```

## Observações

- Na raiz do projeto, há um arquivo HTML chamado `scraped_page_example.html` que mostra o formato de página afetada pelo scraping do script
- Ainda na raiz do projeto, há o arquivo `output_format_example.json`, que mostra como cada imóvel da página é inserido na tabela SQL final `properties`
- O script examina apenas uma única página por vez, para evitar a detecção de bots do site. Caso deseje escanear mais do que uma única página, altere o valor da variável `url` na função `searchZapImoveis` para a página desejada.
  
Exemplo:

```
# first page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=1

# second page
https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo/?__ab=sup-hl-pl:newC,exp-aa-test:control,super-high:new,olx:control,phone-page:control,off-no-hl:new,zapcopsmig:control&transacao=venda&onde=,S%C3%A3o%20Paulo,S%C3%A3o%20Paulo,,,,,city,BR%3ESao%20Paulo%3ENULL%3ESao%20Paulo,-23.555771,-46.639557,&tipos=apartamento_residencial&pagina=2

```

