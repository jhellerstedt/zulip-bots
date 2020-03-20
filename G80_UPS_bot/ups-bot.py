#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 15:40:10 2019

@author: jack
"""

#import os

from typing import Any, Dict

import pickle

from datetime import datetime, timedelta
import pytz


ups_status_file = '/home/jack/zulip-bots/G80_UPS_bot/ups_status.p'
# ups_status_file = os.getcwd() + '/ups_status.p'

## hard-coded path to current pressure pickle:
pressure_status_file = '/home/jack/zulip-bots/G80_UPS_bot/pressure_status.p'

class UPSstatus(object):
    '''
    This bot loads the ups snmp web server and gets the current status values
    '''
    
    def usage(self) -> str:
        return '''
            This bot notifies subscribers if there is a problem with the UPS
        '''
    
    
    
    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        HELP_STR = (
                'Commands:'
                '\n* `@ups-bot help`: display this message'
                '\n* `@ups-bot status`: fetch current ups status'
                '\n* `@ups-bot subscribe`: receive @ notifications of problems'
                '\n* `@ups-bot unsubscribe`: stop receiving @ notifications of problems'
                '\n* `@ups-bot mute <int>`: stop error notifications for <int> minutes; default 30 (no value given)'
                '\n* `@ups-bot pressure`: returns current pressure values'
                '\n* `@ups-pot mute-pressure`: toggle pressure error reporting'
                )
        
        original_content = message['content'].strip()
        command = original_content.split()
        
        if command[0] == 'help' or command[0] == 'Help':
            bot_handler.send_reply(message, HELP_STR)
            return
        
        ## pressure reporting
        elif command[0] == 'mute-pressure' or command[0] == 'Mute-pressure':
            try:
                bot_handler.storage.put('pressure_muted', not bot_handler.storage.get('pressure_muted'))
            except:
                bot_handler.storage.put('pressure_muted', False)
            
            status_message = 'notifications on: ' + str(not bot_handler.storage.get('pressure_muted'))
            bot_handler.send_reply(message, status_message)
           
        elif command[0] == 'pressure' or command[0] == 'Pressure':
            with open(pressure_status_file, 'rb') as f:
                pressure_dict = pickle.load(f)
            
            status_message = ''
            for ii in pressure_dict:
                status_message = status_message + '\n*' + str(ii) + ': ' + str(pressure_dict[ii]) + ' '
            
            bot_handler.send_reply(message, status_message)
            
            try:
                muted = datetime.now() < datetime.strptime(bot_handler.storage.get('unmute_time'), "%Y-%m-%d %H:%M:%S")
            except:
                muted = False
                
            ## don't report pressure problems, Mon-Fri, 8am to 7pm
            hour = datetime.now(pytz.timezone('Australia/Melbourne')).hour
            weekday = datetime.now(pytz.timezone('Australia/Melbourne')).weekday()
            pressure_muted = False
            if hour > 8 and hour < 19 and weekday < 5:
                pressure_muted = True
                try:
                    if bot_handler.storage.get('pressure_muted') is False:
                        pressure_muted = True
                except:
                    bot_handler.storage.put('pressure_muted', False)
                    pressure_muted = True
            
            if pressure_dict['pressure_problem'] is True and pressure_muted is False and muted = False:
                msg_dict = dict(
                    type='stream',
                    to='spm experiments',
                    subject='pressure status',
                    content=status_message,
                )
                bot_handler.send_message(msg_dict)
                
                for subscriber in bot_handler.storage.get('subscribers'):
                    msg_dict = dict(
                        type='private',
                        to=subscriber,
                        subject='pressure problem',
                        content=status_message,
                        )
                    bot_handler.send_message(msg_dict)
                
                bot_handler.storage.put('error_reported', True)
            
            ## all clear message, if problem resolves itself
            try:
                answer = bot_handler.storage.get('error_reported')
            except:
                bot_handler.storage.put('error_reported', False)
            
            if pressure_dict['pressure_problem'] is False and bot_handler.storage.get('error_reported') is True:
                msg_dict = dict(
                        type='stream',
                        to='spm experiments',
                        subject='pressure status',
                        content=status_message,
                        )
                bot_handler.send_message(msg_dict)
                
                for subscriber in bot_handler.storage.get('subscribers'):
                    msg_dict = dict(
                        type='private',
                        to=subscriber,
                        subject='pressure ok',
                        content=status_message,
                        )
                    bot_handler.send_message(msg_dict)
                    
                bot_handler.storage.put('error_reported', False)
                
            return
        
            
        elif command[0] == 'pressure_update_stream':
            with open(pressure_status_file, 'rb') as f:
                pressure_dict = pickle.load(f)
            
            status_message = ''
            for ii in pressure_dict:
                status_message = status_message + '\n* ' + str(ii) + ': ' + str(ups_status[ii]) + ' '
            
            msg_dict = dict(
                            type='stream',
                            to='spm experiments',
                            subject='pressure status',
                            content=status_message,
                            )
            bot_handler.send_message(msg_dict)
            
            
        
        elif command[0] == 'status' or command[0] == 'Status':            
            ## UPS problems
            with open(ups_status_file, 'rb') as f:
                ups_status = pickle.load(f)
            
            status_message = ''
            for ii in ups_status:
                status_message = status_message + '\n* ' + str(ii) + ': ' + str(ups_status[ii]) + ' '
            
            bot_handler.send_reply(message, status_message)
            
            try:
                muted = datetime.now() < datetime.strptime(bot_handler.storage.get('unmute_time'), "%Y-%m-%d %H:%M:%S")
            except:
                muted = False
            
            if ups_status['ups_problem'] is True and muted is False:
                msg_dict = dict(
                        type='stream',
                        to='spm experiments',
                        subject='ups status',
                        content=status_message,
                        )
                bot_handler.send_message(msg_dict)
                
                for subscriber in bot_handler.storage.get('subscribers'):
                    msg_dict = dict(
                        type='private',
                        to=subscriber,
                        subject='ups problem',
                        content=status_message,
                        )
                    bot_handler.send_message(msg_dict)
                    
                bot_handler.storage.put('error_reported', True)
            
            ### send 'all clear' message if power is restored
            try:
                answer = bot_handler.storage.get('error_reported')
            except:
                bot_handler.storage.put('error_reported', False)
            
            if ups_status['ups_problem'] is False and bot_handler.storage.get('error_reported') is True:
                msg_dict = dict(
                        type='stream',
                        to='spm experiments',
                        subject='ups status',
                        content=status_message,
                        )
                bot_handler.send_message(msg_dict)
                
                for subscriber in bot_handler.storage.get('subscribers'):
                    msg_dict = dict(
                        type='private',
                        to=subscriber,
                        subject='power restored',
                        content=status_message,
                        )
                    bot_handler.send_message(msg_dict)
                    
                bot_handler.storage.put('error_reported', False)
                
            return
                
            
        elif command[0] == 'subscribe' or command[0] == 'Subscribe':
            try:
                subscribers = bot_handler.storage.get('subscribers')
                subscribers.append(message['sender_email'])
            except:
                subscribers = [message['sender_email']]
            bot_handler.storage.put('subscribers', subscribers)
            bot_handler.send_reply(message, 'successfully subscribed')
            return
            
        elif command[0] == 'unsubscribe' or command[0] == 'Unsubscribe':
            try:
                current_subscribers = bot_handler.storage.get('subscribers')
                new_subscribers = []
                for subscriber in current_subscribers:
                    if subscriber != message['sender_email']:
                        new_subscribers.append(subscriber)
                bot_handler.storage.put('subscribers', new_subscribers)
                bot_handler.send_reply(message, 'unsubscribed')
            except:
                pass
                bot_handler.send_reply(message, 'error in unsubscribe')
            return
            
        elif command[0] == 'mute' or command[0] == 'Mute':
            try:
                mute_time = int(command[1])
            except:
                mute_time = 30
            unmute_time = str(datetime.now() + timedelta(minutes=mute_time))[:19]
            AEDT_unmute_time = str(datetime.now(pytz.timezone('Australia/Melbourne')) + timedelta(minutes=mute_time))[:19]
            bot_handler.storage.put('unmute_time', unmute_time)
            reply_msg = 'muted until: ' + AEDT_unmute_time
            bot_handler.send_reply(message, reply_msg)
            return
        
        elif command[0] == 'update_stream':
            with open(ups_status_file, 'rb') as f:
                ups_status = pickle.load(f)
            
            status_message = ''
            for ii in ups_status:
                status_message = status_message + '\n* ' + str(ii) + ': ' + str(ups_status[ii]) + ' '
            
            msg_dict = dict(
                            type='stream',
                            to='spm experiments',
                            subject='ups status',
                            content=status_message,
                            )
            bot_handler.send_message(msg_dict)
        
        else:
            bot_handler.send_reply(message, HELP_STR)
            return
        
handler_class = UPSstatus