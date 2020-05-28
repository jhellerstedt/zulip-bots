#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 11:08:43 2019

@author: jack
"""

import time
import pickle

import datetime
from datetime import datetime as dt
import pytz

import zulip

current_pressure_path = '/home/jack/instrument-IO/G80_pressure_logging/current_pressure.p'
pressure_status_file = '/home/jack/zulip-bots/G80_UPS_bot/pressure_status.p'

## second python bot to send a message to ups-bot, so its not self-sending
zulip_config_file = '/home/jack/zulip-bots/G80_UPS_bot/python-zuliprc'


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

    
def get_pressure_status():
    with open(current_pressure_path, 'rb') as f:
        pressure_dict = pickle.load(f)
    
    pressure_status = {}
    pressure_status['pressure_problem'] = False
    pressure_status['timestamp'] = str(dt.now(pytz.timezone('Australia/Melbourne')))[:19]
    
    ## define error conditions for reporting here
    if pressure_dict['LL_pressure'] > 4.5:
        pressure_status['pressure_problem'] = True
    if pressure_dict['prep_pressure'] > 5e-9:
        pressure_status['pressure_problem'] = True
    if pressure_dict['micro_pressure'] > 5e-9:
        pressure_status['pressure_problem'] = True
    
    for ii in pressure_dict:
        pressure_status[ii] = pressure_dict[ii]
        
    return pressure_status


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
    
    return result


alert_bot = True
counter_to_next_alert = 0
status_ok = False
waited_five = False

daily_update_time = dt.now() - datetime.timedelta(days=1)

five_minute_wait = dt.now()

while True:
    pressure_status = get_pressure_status()
    
    with open(pressure_status_file, 'wb') as f:
        pickle.dump(pressure_status, f)
        
    if pressure_status['pressure_problem'] is True and alert_bot is True and waited_five is False:
        if status_ok is True:
            five_minute_wait = dt.now()
        if dt.now() - five_minute_wait > datetime.timedelta(minutes=5):
            status_ok = False
            waited_five = True

    if pressure_status['pressure_problem'] is True and alert_bot is True and waited_five is True:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' pressure_problem, sending alert message')
        result = pressure_send_error(client)
        print(result)
        alert_bot = False
        counter_to_next_alert = 0
        status_ok = False
    
    if pressure_status['pressure_problem'] is True and alert_bot is False:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' ups problem, muted')
        counter_to_next_alert = counter_to_next_alert + 1
        if counter_to_next_alert > 30:
            alert_bot = True
            
    if pressure_status['pressure_problem'] is False and status_ok is False:
        print(str(dt.now(pytz.timezone('Australia/Melbourne')))[:19] + ' power on, sending ok')
        result = pressure_send_error(client)
        status_ok = True
    
    ## send status message 9am every day
    if dt.now(pytz.timezone('Australia/Melbourne')).hour == 9 and dt.now() - daily_update_time > datetime.timedelta(days=1):
        result = pressure_stream_update(client)
        print(result)
        daily_update_time = dt.now() - datetime.timedelta(minutes=10)
    
    time.sleep(15)
