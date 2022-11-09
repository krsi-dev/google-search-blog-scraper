# google-blog-scraper

Search for blogs in google search and convert the page to readable HTML.

## Quickstart

1. `git clone https://github.com/sagowtf-google-blog-scraper`
2. `SERP_API_KEY` in .env
3. `pip install -r requirements.txt`
3. `python . --keywords="example.txt"`

View results in `example.csv`

## Usage

```
usage: python . [-h] --keywords KEYWORDS [--workers WORKERS] [--output-file OUTPUT_FILE] [--max-urls MAX_URLS] [--serp-api-key SERP_API_KEY]

options:
  -h, --help            show this help message and exit
  --keywords KEYWORDS   path to file containing keywords separated by newlines.
  --workers WORKERS     define maximum workers / browsers it will user (default: max)
  --output-file OUTPUT_FILE
                        output file .csv
  --max-urls MAX_URLS   maximum URLs to search in google
  --serp-api-key SERP_API_KEY
                        SERP API key for google search
```