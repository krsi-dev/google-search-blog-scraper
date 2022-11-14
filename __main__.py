import os
import csv
import argparse
from yaml import load
from yaml.loader import SafeLoader
from bleach import clean
from htmlmin import minify
from joblib import Parallel
from joblib import delayed
from itertools import islice
from bs4 import BeautifulSoup
from selenium import webdriver
from serpapi import GoogleSearch

YAML = data = load(
    open("config.yaml", "r"), 
    SafeLoader
)

MAX_WORKERS = YAML["max_workers"]
SERP_API_KEY = YAML["serp_api_key"]
BLACKLIST_URLS = YAML["blacklist_urls"]
WHITELIST_TAGS = YAML["whitelist_tags"]

MAX_URLS = None
OUTPUT_FILE = None


print(YAML)

def array_to_chunk(arr_range, arr_size):
    """turn array to chunks

    Args:
        arr_range (array): list
        arr_size (int): number of chunks

    Returns:
        array: array of chunks
    """
    arr_range = iter(arr_range)
    return iter(lambda: tuple(islice(arr_range, arr_size)), ())

def search_filter(data):
    """filter results from google search

    Args:
        data (array): results from google search

    Returns:
        array: filtered result
    """
    filtered = []

    for dat in data:
        link = dat["link"]
        if not any(blacklist in link for blacklist in BLACKLIST_URLS):
            filtered.append(dat)

    return filtered

def search_google(query):
    """search google

    Args:
        query (str): search query

    Returns:
        array: result from google search
    """
    data = GoogleSearch({
        "q": query,
        "api_key": SERP_API_KEY
    })

    data = data.get_json().get("organic_results")
    print(data)
    data = search_filter(data)
    return data

def get_readable(driver, link):
    """get contens of a lnik using read mode in firefox
    https://github.com/mozilla/readability

    Args:
        driver (selenium): webdriver
        link (str): website link

    Returns:
        str: sanitized html or None
    """

    driver.get("about:reader?url=" + link)
    # force refresh, sometimes firefox reader mode freezes
    driver.refresh()

    # Wait for h1 or title
    h1 = None

    while not h1:
        try:
            # check if content is available
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            h1 = soup.select_one(".reader-title").text != ""
            # skip if content is not available in reader mode
            if "Failed" in soup.title.text:
                break

        except Exception as e:
            # Catch any selenium errors and continue check
            continue
        
    html = None

    if h1:
        html = sanitize_html(driver.page_source)

    return html
        

def sanitize_html(page_source):
    """Clean HTML according to whitelisted tags

    Args:
        page_source (str): driver.page_source

    Returns:
        str: santized HTML
    """

    if not page_source:
        return None
        
    soup = BeautifulSoup(page_source, features="html.parser")
    
    # grab only readable content
    readable = soup.select_one("#readability-page-1")

    # check all image src attribute
    for img in readable.select("img"):
        img_src = img.get("src")
        
        if img_src:
            src = img_src.split('?')[0].split('/')[-1]

            if "." in src:
                # use image filename
                img["src"] = src
            else:
                # no filename fallback
                img["src"] = "#"
        else:
            # no src gets removed
            img.decompose()

    # sanitize
    html = clean(
        str(readable),
        # allowed tags
        tags=WHITELIST_TAGS,
        # allowed attributes
        attributes=["src"],
        
        # remove divs and non allowed tags
        strip=True,
        strip_comments=True
    )

    # Add title
    html = "<h1>" + soup.select_one(".reader-title").text + "</h1>" + html

    # minify code
    html = minify(html)

    return html

def extract_keywords(keywords):
    rows = []
    driver = webdriver.Firefox()

    for keyword in keywords:
        print(keyword)
        col = {"keyword": keyword}

        # get google results
        search_results = search_google(keyword)
        n = 1 
        for search in search_results:
            # break if maximum search is reached
            if n == MAX_URLS + 1:
                break

            link = search["link"]
            print(link)
            html = get_readable(driver, link)
            
            # add html if page is not empty
            if html:
                col[f"url-{n}"] = link
                col[f"html-{n}"] = html
                n += 1
        rows.append(col)
            # or continue scraping until max search reached

    driver.quit()
    return rows

def export_to_csv(rows):
    result = []
    for row in rows:
        result.extend(row)
    
    csv_file = open(OUTPUT_FILE, 'w', newline='', encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    
    count = 0
    for data in result:
        if count == 0:
            header = data.keys()
            csv_writer.writerow(header)
            count += 1
        csv_writer.writerow(data.values())
    
    csv_file.close()




if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python .")
    
    # path to file containing keywords separated by newlines.
    parser.add_argument(
        "input_file",
        type=str,
        help="path to file containing keywords separated by newlines.",
    )

    # output file .csv
    parser.add_argument(
        "output_file",
        type=str,
        help="output file .csv",
        default="output.csv"
    )

    # maximum URLs to search in google (default: 5) (max: -1)
    parser.add_argument(
        'max_urls',
        type=int,
        help="maximum URLs to search in google",
        default=5
    )

    # get arguments
    ARGS = parser.parse_args()

    MAX_URLS = ARGS.max_urls
    OUTPUT_FILE = ARGS.output_file


    # read keyword file
    keywords = [x.strip() for x in open(ARGS.input_file, "r").readlines()]

    # split keywords into chunks X chunks
    # modify number below to add more
    keywords_per_chunk = 30
    keyword_chunks = list(array_to_chunk(keywords, keywords_per_chunk))

    rows = Parallel(n_jobs=MAX_WORKERS)(delayed(extract_keywords)(keywords_) for keywords_ in keyword_chunks)
    
    export_to_csv(rows)
