# GOALS
# 1. Learn complex caching
# 2. Debugging / refactoring
# 3. Challenging scraping problem

import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup as Soup

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CACHE_FNAME = 'cache_file.json'
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DEBUG = True

# -----------------------------------------------------------------------------
# Load cache file
# -----------------------------------------------------------------------------
try:
    with open(CACHE_FNAME, 'r') as cache_file:
        cache_json = cache_file.read()
        CACHE_DICTION = json.loads(cache_json)
except:
    CACHE_DICTION = {}


# -----------------------------------------------------------------------------
# Cache functions
# -----------------------------------------------------------------------------
def has_cache_expired(timestamp_str):
    """Check if cache timestamp is over expire_in_days old"""
    # gives current datetime
    now = datetime.now()

    # datetime.strptime converts a formatted string into datetime object
    cache_timestamp = datetime.strptime(timestamp_str, DATETIME_FORMAT)

    # subtracting two datetime objects gives you a timedelta object
    delta = now - cache_timestamp
    delta_in_days = delta.days

    # now that we have days as integers, we can just use comparison
    # and decide if cache has expired or not
    if delta_in_days > expire_in_days:
        return False
    else:
        return True


def get_from_cache(url):
    """If URL exists in cache and has not expired, return the html, else return None"""
    if url in CACHE_DICTION:
        url_dict = CACHE_DICTION[url]

        if has_cache_expired(url_dict['timestamp'], url_dict['expire_in_days']):
            # also remove old copy from cache
            del CACHE_DICTION[url]
            html = None
        else:
            html = CACHE_DICTION[url]['html']
    else:
        html = None

    return html


def set_in_cache(url, html, expire_in_days):
    """Add URL and html to the cache dictionary, and save the whole dictionary to a file as json"""
    CACHE_DICTION[url] = {
        'html': html,
        'timestamp': datetime.now().strftime(DATETIME_FORMAT),
        'expire_in_days': expire_in_days
    }

    with open(CACHE_FNAME, 'w') as cache_file:
        cache_json = json.dumps(CACHE_DICTION)
        cache_file.write(cache_json)


def get_html_from_url(url, expire_in_days=7):
    """Check in cache, if not found, load html, save in cache and then return that html"""
    # check in cache
    html = get_from_cache(url)
    if html:
        if DEBUG:
            print('Loading from cache: {0}'.format(url))
            print()
    else:
        if DEBUG:
            print('Fetching a fresh copy: {0}'.format(url))
            print()

        # fetch fresh
        response = requests.get(url)

        # this prevented encoding artifacts like
        # "Trumpâs Tough Talk" that should have been "Trump's Tough Talk"
        response.encoding = 'utf-8'

        html = response.text

        # cache it
        set_in_cache(url, html, expire_in_days)

    return html


# -----------------------------------------------------------------------------
# Let's parse NYTimes Today's Paper
# -----------------------------------------------------------------------------

todays_paper_html = get_html_from_url("http://www.nytimes.com/pages/todayspaper/index.html", expire_in_days=1)
todays_soup = Soup(todays_paper_html, 'html.parser')

# 1. Section Articles
# =================== #

# We design it by starting with only the front page section,
# and then generalize it for every section
def load_articles_from_section(section_soup):
    story_list = []
    stories = section_soup.find_all('div', {'class': 'story'})
    for story_soup in stories:
        story_dict = extract_data_from_story_item(story_soup)
        story_dict['related_articles'] = extract_related_articles(story_dict['url'])
        story_list.append(story_dict)

        if DEBUG:
            print(story_dict['title'])
            print(story_dict['byline'])
            print(story_dict['summary'])
            print("Has Thumbnail: ", story_dict['thumbnail'] and True or False)
            print("Has URL:", story_dict['url'] and True or False)
            print("# of related articles:", len(story_dict['related_articles']))
            print()
            print('-'*10)
            print()

    return story_list

def extract_data_from_story_item(story_soup):
    title = story_soup.find('h3').text.strip()
    byline = story_soup.find('h6').text.strip()

    summary_p = story_soup.find('p', {'class': 'summary'})
    if summary_p:
        summary = summary_p.text.strip()
    else:
        summary = None

    thumbnail = None
    img_tag = story_soup.find('img')
    if img_tag:
        thumbnail = img_tag.get('src')

    # and some other ways of doing this
    # thumbnail = img_tag.get('src') if img_tag else None
    # thumbnail = img_tag and img_tag.get('src') or None

    url = story_soup.find('h3').find('a').get('href')

    story_dict = {
        'title': title,
        'byline': byline,
        'summary': summary,
        'thumbnail': thumbnail,
        'url': url
    }

    return story_dict

# 1.1 Section Articles with Headlines Only
# ======================================== #

def load_articles_from_headlines_only(section_soup):
    story_list = []
    stories = section_soup.find_all('li')
    for story_soup in stories:
        story_dict = {
            'title': story_soup.find('h6').text.strip(),
            'url': story_soup.find('a').get('href')
        }

        byline_tag = story_soup.find('div', {'class': 'byline'})
        story_dict['byline'] = byline_tag.text.strip() if byline_tag else None

        story_dict['related_articles'] = extract_related_articles(story_dict['url'])
        story_list.append(story_dict)

        if DEBUG:
            print(story_dict['title'])
            if story_dict.get('byline'):
                print(story_dict['byline'])
            print("Has URL:", story_dict['url'] and True or False)
            print("# of related articles:", len(story_dict['related_articles']))
            print()
            print('-'*10)
            print()

    return story_list

# 2. Related Articles
# =================== #

def extract_related_articles(url):
    related_coverage_list = []

    story_html = get_html_from_url(url)
    story_soup = Soup(story_html, 'html.parser')
    related_soup = story_soup.find('aside', {'class': 'related-combined-coverage-marginalia'})

    if related_soup:
        for article_soup in related_soup.find_all('li'):
            article_dict = extract_data_from_related_article(article_soup)
            related_coverage_list.append(article_dict)

    return related_coverage_list


def extract_data_from_related_article(article_soup):
    title = article_soup.find('h2').text.strip()

    img_tag = article_soup.find('img')
    thumbnail = img_tag.get('src') if img_tag else None

    url = article_soup.find('a').get('href')

    return {
        'title': title,
        'thumbnail': thumbnail,
        'url': url
    }


# 3. It all comes together here / or everything starts here
# ========================================================= #

if DEBUG: print('The Front Page'.upper())
front_page_soup = todays_soup.find('div', {'class': 'aColumn'})
load_articles_from_section(front_page_soup)
load_articles_from_headlines_only(front_page_soup.find('ul', {'class': 'headlinesOnly'}))

other_sections = todays_soup.find('div', {'id': 'SpanABMiddleRegion'})
for section_soup in other_sections.find_all('ul', {'class': 'headlinesOnly'}):
    section_title = section_soup.parent.find('h3', {'class': 'sectionHeader'}).text.strip()
    if DEBUG:
        print()
        print('='*len(section_title))
        print(section_title.upper())
        print('='*len(section_title))
        print()

    load_articles_from_headlines_only(section_soup)
