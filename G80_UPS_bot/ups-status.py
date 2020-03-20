#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 11:08:43 2019

@author: jack
"""

import os

import atexit

import time
import pickle

import datetime
from datetime import datetime as dt
import pytz
from splinter import Browser

import zulip

ups_status_file = '/home/jack/zulip_bots/ups_bot/ups_status.p'
current_pressure_path = '/home/jack/instrument-IO/G80_pressure_logging/current_pressure.p'
pressure_status_file = '/home/jack/zulip_bots/G80_UPS_bot/pressure_status.p'

## second python bot to send a message to ups-bot, so its not self-sending
zulip_config_file = '/home/jack/zulip_bots/ups_bot/python-zuliprc'
# zulip_config_file = os.getcwd() + '/zuliprc'
# ups_status_file = os.getcwd() + '/ups_status.p'

client = zulip.Client(config_file=str(zulip_config_file))


## address to send message to, .e.g., ups-bot
ups_bot_address = 'ups-bot-bot@nedchat.imipolex.biz'

with open(zulip_config_file) as f:
    d = f.readline() # just the [api] bit
    d = f.readline() # address
    d = d.strip('email=')
    d = d.strip('\n')
    python_bot_address = d

print('sending bot address: ' + python_bot_address)

print('receiving bot address: ' + ups_bot_address)

def get_status_dict(browser):
    ups_status = {}
    ups_status['ups_problem'] = False
        
    xpaths_to_read = {
            'upsMode':'//*[@id="upsMode"]',
            'upsTemp':'//*[@id="upsTemp"]',
            'warning':'//*[@id="warning"]',
            'batteryVoltage':'//*[@id="batteryVoltage"]',
            'batteryCapacity':'//*[@id="batteryCapacity"]',
            'backupTime':'//*[@id="backupTime"]',
            'Load level L1':'//*[@id="loadLevel"]',
            'Load level L2':'//*[@id="loadLevelS"]',
            'Load level L3':'//*[@id="loadLevelT"]'
            }
    try:
        for variable in xpaths_to_read:
            ups_status[variable] = browser.find_by_xpath(xpaths_to_read[variable]).first.value
        
        ups_status['timestamp'] = str(dt.now(pytz.timezone('Australia/Melbourne')))[:19]
        
        if ups_status['upsMode'] != 'Line Mode':
            ups_status['ups_problem'] = True
            if ups_status['upsMode'] == '---':
                ups_status['warning'] = 'website not loaded'
        if ups_status['warning'] != '':
            ups_status['ups_problem'] = True
        if float(ups_status['upsTemp']) > 43:
            ups_status['ups_problem'] = True
        if float(ups_status['batteryCapacity']) < 90:
            ups_status['ups_problem'] = True
    except:
        ups_status['timestamp'] = str(dt.now(pytz.timezone('Australia/Melbourne')))[:19]
        ups_status['warning'] = "site unreachable"
        ups_status['ups_problem'] = True
            
        
    return ups_status
    
def get_pressure_status():
    with open(current_pressure_path, 'rb') as f:
        pressure_dict = pickle.load(f)
    
    pressure_status = {}
    pressure_status['pressure_problem'] = False
    pressure_status['timestamp'] = str(dt.now(pytz.timezone('Australia/Melbourne')))[:19]
    
    ## define error conditions for reporting here
    if pressure_dict['LL_pressure'] > 1.3:
        pressure_status['pressure_problem'] = True
    if pressure_dict['prep_pressure'] > 5e-9:
        pressure_status['pressure_problem'] = True
    if pressure_dict['micro_pressure'] = 5e-10:
        pressure_status['pressure_problem'] = True
    
    for ii in pressure_dict:
        pressure_status[ii] = pressure_dict[i]
    
    with open(pressure_status_file, 'wb') as f:
        pickle.dump(pressure_status, f)


def pressure_send_error(client):
    msg = {
        'type': 'private',
        'to': ups_bot_address,
        'content': 'pressure'
    }
    result = client.send_message(msg)
    
    return result
    
def pressure_stream_update(client):
    msg = {
        'type': 'private',
        'to': ups_bot_address,
        'content': 'pressure_update_stream'
    }
    result = client.send_message(msg)
    
def send_error_msg(client):
    msg = {
        "type": "private",
        "to": ups_bot_address,
        "content": "status"
    }
    result = client.send_message(msg)
    
    return result

def send_stream_update(client):
    msg = {
        "type": "private",
        "to": ups_bot_address,
        "content": "update_stream"
    }
    result = client.send_message(msg)
    
    return result
    


def handle_exit():
    print('trying to close browser')
    try:
        browser.quit()
    except:
        pass
    
atexit.register(handle_exit)


    
browser = Browser('firefox', headless=True, timeout=15)

url = "http://130.194.160.71/sys_status.html?qpi=10_3/3_1_0"

page_loaded = True
try:
    browser.visit(url=url)
    time.sleep(20)
except:
    page_loaded = False
    print('initial load failed')
    
tries = 0
alert_bot = True
counter_to_next_alert = 0
status_ok = False

restart_browser_time = dt.now() + datetime.timedelta(hours=4)

daily_update_time = dt.now() - datetime.timedelta(days=1)

while True:
    while ((page_loaded is False) and (tries < 3)):
        try:
            browser.reload()
            time.sleep(15)
            ups_status = get_status_dict(browser)
            if ups_status['warning'] != 'site unreachable':
                page_loaded = True
        except:
            page_loaded = False
        
        counter_to_next_alert = counter_to_next_alert + 15
        tries = tries + 1
        
    tries = 0
    
    ups_status = get_status_dict(browser)
    
    ## change the ups_problem to True for testing purposes:
    # ups_status['ups_problem'] = True
    
    with open(ups_status_file, 'wb') as f:
        pickle.dump(ups_status, f)

    if ups_status['ups_problem'] is True and alert_bot is True:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' ups_problem, sending alert message')
        result = send_error_msg(client)
        print(result)
        alert_bot = False
        counter_to_next_alert = 0
        status_ok = False
    
    if ups_status['ups_problem'] is True and alert_bot is False:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' ups problem, muted')
        counter_to_next_alert = counter_to_next_alert + 1
        if counter_to_next_alert > 30:
            alert_bot = True
            
    if ups_status['ups_problem'] is False and status_ok is False:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' power on, sending ok')
        result = send_error_msg(client)
        status_ok = True
        
    if ups_status['warning'] == 'site unreachable' or ups_status['upsMode'] == '---':
        page_loaded = False
    
    ## send status message 9am every day
    if dt.now(pytz.timezone('Australia/Melbourne')).hour == 9 and dt.now() - daily_update_time > datetime.timedelta(days=1):
        result = send_stream_update(client)
        print(result)
        daily_update_time = dt.now() - datetime.timedelta(minutes=10)
    
    ## restart browser every 24 hours to stop memory leak problem
    if ups_status['ups_problem'] is False and dt.now() - restart_browser_time > datetime.timedelta(days=1):
        browser.quit()
        time.sleep(10) 
        browser = Browser('firefox', headless=True, timeout=15)
        url = "http://130.194.160.71/sys_status.html?qpi=10_3/3_1_0"
        page_loaded = True
        try:
            browser.visit(url=url)
            restart_browser_time = dt.now()
            time.sleep(20)
        except:
            page_loaded = False
            print('restart failed')
        
    
    time.sleep(15)
