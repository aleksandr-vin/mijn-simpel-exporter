from prometheus_client import start_http_server, Summary, Gauge, Info
import schedule
import time
from mijn_simpel.client import Session, Subscription
from os.path import expanduser
import os
import sys
import logging
import configparser

config = configparser.ConfigParser()
if len(sys.argv) > 1:
    config.read(sys.argv[1])
else:
    config.read('mijn_simpel_exporter.ini')

logging.basicConfig(level=logging.DEBUG)

SCRAPE_TIME = Summary('scrape_processing_seconds', 'Time spent processing scrape of mijn simpel')
LOGIN_TIME = Summary('login_processing_seconds', 'Time spent processing login on mijn simpel')
SUBSCRIPTIONS_TIME = Summary('subscriptions_processing_seconds', 'Time spent processing subscriptions on mijn simpel')
USAGE_SUMMARY_TIME = Summary('usage_summary_processing_seconds', 'Time spent processing usage summary on mijn simpel')
DATA_AMOUNT_LEFT = Gauge('data_amount_left', 'Data amount left in a month for subscription', ['subscription', 'msisdn'])
ONE_OFF_BUNDLE_AMOUNT_LEFT = Gauge('one_off_bundle_amount_left', 'One off bundle amount left in a month for subscription', ['subscription', 'msisdn'])
CEILING_CONSUMPTION = Gauge('ceiling_consumption', 'Ceiling consumption in a month for subscription', ['subscription', 'msisdn'])
ABROAD_DATA_AMOUNT_LEFT = Gauge('abroad_data_amount_left', 'Abroad data amount left in a month for subscription', ['subscription', 'msisdn'])
SMS_AMOUNT_LEFT = Gauge('sms_amount_left', 'SMS amount left in a month for subscription', ['subscription', 'msisdn'])
VOICE_AMOUNT_LEFT = Gauge('voice_amount_left', 'Voice amount left in a month for subscription', ['subscription', 'msisdn'])

username = config['main'].get('username', os.environ.get('MIJN_SIMPEL_USERNAME', None))
password = config['main'].get('password', os.environ.get('MIJN_SIMPEL_PASSWORD', None))
cookie_jar = config['main'].get('cookie-jar', expanduser("~") + '/.config/mijn-simpel-cookie')
port = config['main'].getint('port', 9151)
scrape_interval = config['main'].getint('scrape-interval-minutes', 15) # min
s = Session(cookie_jar)

i = Info('mijn_simpel_exporter', 'Description of info')
i.info({'version': 'dev', 'port': str(port), 'scrape-interval-minutes': str(scrape_interval)})

@LOGIN_TIME.time()
def login(username, password):
    return s.login(username, password)

@SUBSCRIPTIONS_TIME.time()
def subscriptions():
    return s.account_subscription_overview()

@USAGE_SUMMARY_TIME.time()
def usage_summary(subscription_id, msisdn):
    subscription = s.subscription(subscription_id)
    resp = subscription.usage_summary()
    assert(resp)
    if resp['dataAmountLeft']:
        DATA_AMOUNT_LEFT.labels(subscription=subscription_id, msisdn=msisdn).set(resp['dataAmountLeft'])
    if resp['oneOffBundleAmountLeft']:
        ONE_OFF_BUNDLE_AMOUNT_LEFT.labels(subscription=subscription_id, msisdn=msisdn).set(resp['oneOffBundleAmountLeft'])
    if resp['ceilingConsumption']:
        CEILING_CONSUMPTION.labels(subscription=subscription_id, msisdn=msisdn).set(resp['ceilingConsumption'])
    if resp['abroadDataAmountLeft']:
        ABROAD_DATA_AMOUNT_LEFT.labels(subscription=subscription_id, msisdn=msisdn).set(resp['abroadDataAmountLeft'])
    if resp['smsAmountLeft']:
        SMS_AMOUNT_LEFT.labels(subscription=subscription_id, msisdn=msisdn).set(resp['smsAmountLeft'])
    if resp['voiceAmountLeft']:
        VOICE_AMOUNT_LEFT.labels(subscription=subscription_id, msisdn=msisdn).set(resp['voiceAmountLeft'])

def init():
    if not(os.path.exists(cookie_jar)):
        resp = login(username, password)
        assert(resp)
        logging.debug("Logged in mijn simpel")
    resp = subscriptions()
    if not(resp):
        resp = login(username, password)
        assert(resp)
        logging.debug("Logged in mijn simpel")
        resp = subscriptions()
        assert(resp)
    global subs
    subs = resp['linkedSubscriptions']
    subs.append(resp['mainSubscription'])
    logging.debug(f"Fetched subscriptions: {subs}")
        
@SCRAPE_TIME.time()
def process_scrape():
    for s in subs:
        usage_summary(s['subscriptionId'], s['msisdn'])
    
def job():
    process_scrape()

    
if __name__ == '__main__':
    start_http_server(port)
    init()
    process_scrape()
    logging.debug(f"Scheduling scrape every {scrape_interval} minutes")
    schedule.every(scrape_interval).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)


