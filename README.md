# google-blog-scraper

Search for blogs in google search and convert the page to readable HTML.

## Quickstart

1. `git clone https://github.com/sagowtf-google-blog-scraper`
2. `config.yml` add SERP API key
3. `pip install -r requirements.txt`
3. `python . [input_file] [output_file] [max_urls]"`
4. `python . example.txt example.csv 5`

View results in `example.csv`


## Usage

```
usage: python . [-h] input_file output_file max_urls

positional arguments:
  input_file   path to file containing keywords separated by newlines.
  output_file  output file .csv
  max_urls     maximum URLs to search in google

options:
  -h, --help   show this help message and exit
```

## Config

`config.yml` to edit configuration.

1. max_workers:  -1 maximum browsers the machine can open
2. serp_api_key: google search
3. blacklist_text: blacklisted words when sanitizing HTML
4. blacklist_urls: blacklisted URLs when searching for google results
5. whitelist_tags: whitelisted HTML tags