import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from os import path

# Constents
UFC_WIKI_EVENTS_URL = 'https://en.wikipedia.org/wiki/List_of_UFC_events'
TWO_MONTHS = [datetime.now().month, datetime.now().month+1]
EVENTS_FILENAME = 'events.json'

def get_soup(url):
    page = requests.get(url)
    return BeautifulSoup(page.content, 'html.parser')

def get_scheduled_events(soup):
    events = soup.find('table', id='Scheduled_events')
    table =  events.find('tbody')
    return table.find_all('tr')[1:]

def get_events_details(rows):
    filtered_events = []
    for row in rows:
        tds = row.find_all('td')
        event_name = tds[0].get_text().replace('\n','')
        event_date = datetime.strptime(tds[1].get_text().replace('\n',''), "%b %d, %Y").date()
        if event_date.month in TWO_MONTHS:
            filtered_events.append({'event_name':event_name, 'event_date':str(event_date)})
    return filtered_events

def upsert_events(all_events):
    if not path.exists(EVENTS_FILENAME): open(EVENTS_FILENAME, 'w').close()
    with open(EVENTS_FILENAME, 'r') as f:
        json_events = json.load(f)
        has_changes = False
        for event in all_events:
            if event not in json_events:
                json_events.append(event)
                has_changes = True
        if has_changes:
            with open(EVENTS_FILENAME, 'w') as outfile:
                json.dump(json_events, outfile)

if __name__ == '__main__':
    # this should be run once a month.
    soup = get_soup(UFC_WIKI_EVENTS_URL)
    rows = get_scheduled_events(soup)
    all_events = get_events_details(rows)
    upsert_events(all_events)


