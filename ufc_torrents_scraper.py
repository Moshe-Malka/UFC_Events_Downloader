import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
from datetime import datetime
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

VERBOSE = False
DEBUG = TRUE
BITTORENT_RUL = 'https://btweb.trontv.com/gui/index.html?v=1.0.7.2340&localauth=localapi1ff8ecf42ea89180:'
QUALITY_OPTIONS = {'1080p': 100, '720p': 85, '540p': 65, '480p': 45, 'hdtv': 40, 'webrip': 35, 'web-dl': 25, 'web': 10}
KEYWORDS_TO_EXCLUDE = ['weigh-in', 'embedded', 'inside the octagon', 'countdown']
EVENTS_FILENAME = 'events.json'

options = Options()
if DEBUG: options.headless = True
driver = webdriver.Chrome(options=options)

def read_events_file():
    ready_events = []
    with open(EVENTS_FILENAME, 'r') as f:
        json_events = json.load(f)
        for event in json_events:
            if datetime.today().date() > datetime.strptime(event['event_date'], "%Y-%m-%d").date():
                ready_events.append(event)
        events_left = [x for x in json_events if x not in ready_events] if ready_events else []
        return (ready_events, events_left)

def write_events_file(data):
    with open(EVENTS_FILENAME, 'w') as f: json.dump(data, f)

def get_soup(url):
    page = requests.get(url)
    return BeautifulSoup(page.content, 'html.parser')

def get_quality(name):
    if name in QUALITY_OPTIONS:
        return { 'quality_name': name, 'quality_amount': QUALITY_OPTIONS[name] }
    else:
        return { 'quality_name':'Unknown Quality', 'quality_amount': 50 }

def get_table_body(soup):
    t_body = soup.select('#searchResult > tr')
    return t_body if t_body else []

def get_data(row):
    cols = row.findChildren('td', recursive=False)
    name = cols[1].get_text().replace('.', ' ').replace('\n', '').lower()
    uploaded = cols[2].get_text().replace(u'\xa0', ' ')
    magnet = cols[3].select_one('[href^=magnet]').get_attribute_list('href')[0]
    seeders = cols[5].get_text()
    return name, uploaded, magnet, seeders

def download_magnet(magnet):
    if magnet:
        driver.get(BITTORENT_RUL)

        time.sleep(2)
        add_btn = driver.find_element_by_id('auto-upload-btn')
        add_btn.click()
        time.sleep(2)

        magnet_input = driver.find_element_by_css_selector('.link-input-container > input[name="link"]')
        magnet_input.send_keys(magnet)
        time.sleep(2)

        add_torrent_btn = driver.find_element_by_id('add-torrent-url-btn')
        add_torrent_btn.click()
        time.sleep(2)

        confirm_btn = driver.find_element_by_css_selector('.add-torrent-btn.modal-footer-right-button.button--secondary')
        confirm_btn.click()
        time.sleep(2)

        driver.get(BITTORENT_RUL)
        time.sleep(2)

def calculate_optimal(obj):
    return obj.get('seeders', 0) + obj.get('quality', {}).get('quality_amount', 1)

def get_optimal(options):
    if len(options) == 0: return None
    elif len(options) == 1: return options[0]
    else:
        optimal = options[0]
        for option in options[1:]:
            if calculate_optimal(option) > calculate_optimal(optimal): optimal = option
        return optimal

def process_one_event(t_body):
    early = prelims = all_other = []
    for tr in t_body:
        if tr.select("img[alt='Next']"):
            if VERBOSE: print(f'Skipping ... - end of page (pagination)')
            continue
        t_name, t_uploaded, t_magnet, t_seeders = get_data(tr)
        if any([x for x in KEYWORDS_TO_EXCLUDE if x in t_name]):
            if VERBOSE: print(f'Skipping {t_name} - Exclude Keywords in Torrent Name ({[x for x in KEYWORDS_TO_EXCLUDE if x in t_name]})')
            continue
        
        if int(t_seeders) < 5:
            if VERBOSE: print(f'Skipping {t_name} - Low Seeders Count ({t_seeders})')
            continue

        obj = {
            'torrent_name': t_name,
            'torrent_date_uploaded': t_uploaded,
            'magnet_link': t_magnet,
            'seeders': t_seeders,
            'quality': get_quality(t_name)
        }

        if 'early prelims' in t_name: early.append(obj)
        elif 'prelims' in t_name or 'prelimes' in t_name: prelims.append(obj)
        else: all_other.append(obj)
    return early, prelims, all_other

def process_events(events):
    for event in events:
        event_name = event.get('event_name')
        enc_val = urllib.parse.quote(event_name)
        url = f'https://piratebay.party/search/{enc_val}'
        soup = get_soup(url)
        table_body = get_table_body(soup)
        early_prelims, prelims, all_other = process_one_event(table_body)
        to_download = [
            get_optimal(early_prelims),
            get_optimal(prelims),
            get_optimal(all_other)
        ]
        
        for d in to_download:
            if d: download_magnet(d.get('magnet_link', None)) 

if __name__ == '__main__':
    ready_events, events_left = read_events_file()
    if ready_events:
        process_events(ready_events)
        # at the end - delete events we processed from events file.
        write_events_file(events_left)

