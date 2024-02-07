# Get all Reuters articles about grain tenders for year 2022
import logging as logger
import csv
import re
from datetime import datetime, timedelta
import time
import eikon as ek
from bs4 import BeautifulSoup
import os, sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from sales_report_library import *

initialize_logger(logging_directory='log', console_level='INFO')

# connect to eikon with api key
params = config(filename='..\generic.ini', section='eikon_api')
try:
    ek.set_app_key(params['apikey'])
except:
    logger.info('Connecting to eikon failed. Try again in 60s')
    time.sleep(60)
    try:
        ek.set_app_key(params['apikey'])
    except:
        logger.error('Could not connect to eikon. Probably logged out.')
        exit(1)

# create a CSV file we will save our data to
csv_file = 'tender_reuters_articles_new.csv'
with open(csv_file, 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['id', 'created_date', 'headline', 'text']
    writer.writerow(header)

date_from = '2022-01-01T00:00:00'
#date_to = '2023-12-31T23:59:59'
date_to = '2024-02-07T10:46:00'

while date_to > date_from:
    # get all relevant Reuters news articles
    logger.info(f'Getting data from {date_from} to {date_to}.')
    logger.info('Extracting headlines')
    headlines_raw = ek.get_news_headlines('grains AND tender AND (GASC OR Tunisia OR Algeria) ', count=100, date_from=date_from, date_to=date_to)
    logger.info('Extracted headlines')
    data = pd.DataFrame(headlines_raw)  # convert to pandas dataframe

    # get article headlines, ids and created dates
    article_headlines = list(data['text'])
    article_ids = list(data['storyId'])
    article_created_dates = list(data['versionCreated'])

    # update date_to
    # set it to the last extracted created date minus one minute to make sure we don't get duplicates
    if article_created_dates:
        date_to = str(article_created_dates[-1])
        date_to = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S%z')
        date_to = date_to - timedelta(minutes=1)
        date_to = date_to.strftime('%Y-%m-%dT%H:%M:%S')
    # if we got nothing, we stop
    else:
        date_to = date_from

    # based on the article's id, get article's text
    logger.info("Retrieving and cleaning articles' texts.")
    article_texts = []
    for article_id in article_ids:
        article_text = []
        article_text_html = ek.get_news_story(article_id)
        soup = BeautifulSoup(article_text_html, features='html.parser')
        article_text_html = soup.prettify()
        soup = BeautifulSoup(article_text_html, 'html.parser')
        p_elements = soup.find_all('p')

        for p in p_elements:
            paragraph = p.getText()
            paragraph = paragraph.replace('\n', ' ')
            paragraph = paragraph.strip()
            paragraph = re.sub(r' +', ' ', paragraph)
            # take the main text (without Reuters date and place of report, person reporting, their contact info, etc.)
            intro: list = re.findall(r'\(Reuters\) - (.+)', paragraph)
            final_line: list = re.findall(r'(?i)(Reporting by)|(Compiled by)', paragraph)
            if intro:
                paragraph = intro[0]
            if not final_line:
                article_text.append(paragraph)
            elif final_line:
                break

        # clean the text
        article_text = ' '.join(article_text).strip()
        # append the text for the current article to the list with texts for all articles
        article_texts.append(article_text)

    logger.info("Retrieved and cleaned articles' texts.")

    # save the data to CSV
    logger.info('Saving data to CSV.')
    csv_file = 'tender_reuters_articles_new.csv'
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for id, date, headline, text in zip(article_ids, article_created_dates, article_headlines, article_texts):
            data = [id, date, headline, text]
            writer.writerow(data)

    logger.info('Saved data to CSV.')
logger.info('All data is saved.')
