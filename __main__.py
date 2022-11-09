import os
import csv
import argparse
from bleach import clean
from htmlmin import minify
from joblib import Parallel
from joblib import delayed
from itertools import islice
from bs4 import BeautifulSoup
from selenium import webdriver
from dotenv import load_dotenv
from serpapi import GoogleSearch

# add blacklisted urls i.e amazon yotube 
BLACKLIST_URLS = ["amazon", "youtube", "pinterest", "book"]

# add whitelisted HTML tags
WHITELIST_TAGS = ["b", "p", "a", "h1", "h2", "h3", "h4", "h5", "h6", "img", "ul", "ol", "li", "table", "thead", "tbody", "th", "tr"]

load_dotenv()


def chunk(arr_range, arr_size):
    # turn array into chunks
    arr_range = iter(arr_range)
    return iter(lambda: tuple(islice(arr_range, arr_size)), ())

def firefox_readability(keywords, args):


    rows = []
    driver = webdriver.Firefox()

    for keyword in keywords:
        j = {"keyword": keyword}

        search = GoogleSearch({
            "q": keyword, 
            "api_key": args.serp_api_key
        })

        results = search.get_json()
        results_organic = results.get("organic_results") or []
        # remove blacklisted URLs
        results_links = [x for x in results_organic[1:args.max_urls+1] if not any(ext in x["link"] for ext in BLACKLIST_URLS)]

        for i, r in enumerate(results_links):
            link = r["link"]
            n = i + 1
            print(link)

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
                    raise e
                    # Catch any selenium errors and continue check
                    continue
                
            html = None

            if h1:
                html = sanitize_html(driver.page_source)

            j[f"url-{n}"] = link
            j[f"html-{n}"] = html
        
        rows.append(j)
    
    driver.quit()

    return rows
        

def sanitize_html(source):
    # don't do anything if no source is found
    if not source:
        return
        
    soup = BeautifulSoup(source, features="html.parser")
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python .")
    
    # path to file containing keywords separated by newlines.
    parser.add_argument(
        "--keywords",
        type=str,
        help="path to file containing keywords separated by newlines.",
        required=True
    )

    # define maximum workers / browsers it will user (default: max)
    parser.add_argument(
        "--workers",
        type=int,
        help="define maximum workers / browsers it will user (default: max)",
        default=-1
    )
    
    # output file .csv
    parser.add_argument(
        "--output-file",
        type=str,
        help="output file .csv",
        default="output.csv"
    )

    # maximum URLs to search in google (default: 5) (max: -1)
    parser.add_argument(
        '--max-urls',
        type=int,
        help="maximum URLs to search in google",
        default=5
    )

    # SERP API key for google search
    # default SERP_API_KEY in .env file
    parser.add_argument(
        '--serp-api-key',
        type=str,
        help="SERP API key for google search",
        default=os.environ.get("SERP_API_KEY")
    )
    
    # get arguments
    args = parser.parse_args()


    # read keyword file
    keywords = [x.strip() for x in open(args.keywords, "r").readlines()]

    # split keywords into chunks X chunks
    # modify number below to add more
    keywords_per_chunk = 30
    keyword_chunks = list(chunk(keywords, keywords_per_chunk))

    rows = Parallel(n_jobs=args.workers)(delayed(firefox_readability)(keywords_, args) for keywords_ in keyword_chunks)

    # append all rows to one result
    result = []
    for row in rows:
        result.extend(row)
    

    # finally save all result to one CSV file
    data_file = open(args.output_file, 'w', newline='', encoding="utf-8")
    csv_writer = csv.writer(data_file)
    
    count = 0
    for data in result:
        if count == 0:
            header = data.keys()
            csv_writer.writerow(header)
            count += 1
        csv_writer.writerow(data.values())
    
    data_file.close()
