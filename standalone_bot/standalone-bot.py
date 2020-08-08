#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2020-8-8 1400

@author: jack
"""

#import os

from typing import Any, Dict

import pickle

from datetime import datetime, timedelta
import pytz


## hard-coded path to current pressure pickle:
pressure_status_file = '/home/jack/zulip-bots/standalone_bot/pressure_status.p'

class PressureStatus(object):
    '''
    This bot just does pressure reporting/ interaction through zulip
    '''
    
    def usage(self) -> str:
        return '''
            This bot notifies subscribers if there is a problem with the UPS
        '''
    
    
    
    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        HELP_STR = (
                'Commands:'
                '\n* `@ups-bot help`: display this message'
                '\n* `@ups-bot subscribe`: receive @ notifications of problems'
                '\n* `@ups-bot unsubscribe`: stop receiving @ notifications of problems'
                '\n* `@ups-bot mute <int>`: stop error notifications for <int> minutes; default 30 (no value given)'
                '\n* `@ups-bot pressure`: returns current pressure values'
                '\n* `@ups-bot mute-pressure`: toggle pressure error reporting'
                '\n* `@ups-bot list_subscribers`: list current subscribers'
                '\n* `@ups-bot bakeout <int>`: set pressure error threshold to 3E-6 for <int> hours; default 48 (no value given)'
                )
        
        original_content = message['content'].strip()
        command = original_content.split()
        
        
        bakeout_pressure_threshold = 3E-6
        
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
            return
        
        elif command[0] == 'bakeout' or command[0] == 'Bakeout':
            try:
                bakeout_time = int(command[1])
            except:
                bakeout_time = 48
            
            bakeout_finish_time = str(datetime.now() + timedelta(hours=bakeout_time))[:19]
            bot_handler.storage.put('bakeout_finish_time', bakeout_finish_time)
            AEDT_bakeout_finish_time = str(datetime.now(pytz.timezone('Australia/Melbourne')) + timedelta(hours=bakeout_time))[:19]
            reply_msg = 'bakeout until: ' + AEDT_bakeout_finish_time
            bot_handler.send_reply(message, reply_msg)
            return
            
           
        elif command[0] == 'pressure' or command[0] == 'Pressure':
            with open(pressure_status_file, 'rb') as f:
                pressure_dict = pickle.load(f)
            
            try:
                muted = datetime.now() < datetime.strptime(bot_handler.storage.get('unmute_time'), "%Y-%m-%d %H:%M:%S")
            except:
                muted = False
                
            ## bakeout condition: set problem to false for higher pressure threshold
            try:
                baking = datetime.now() < datetime.strptime(bot_handler.get('bakeout_finish_time'), "%Y-%m-%d %H:%M:%S")
            except:
                baking = False
            if baking is True:
                if pressure_dict['prep_pressure'] < bakeout_pressure_threshold: ## prep pressure threshold
                    pressure_dict['pressure_problem'] = False
                    pressure_dict['baking'] = True
                
            ## don't report pressure problems, Mon-Fri, 8am to 7pm
            hour = datetime.now(pytz.timezone('Australia/Melbourne')).hour
            weekday = datetime.now(pytz.timezone('Australia/Melbourne')).weekday()
            
            try:
                pressure_muted = bot_handler.storage.get('pressure_muted')
            except:
                bot_handler.storage.put('pressure_muted', False)
                pressure_muted = False 
            
            if hour > 8 and hour < 19 and weekday < 5:
                pressure_muted = True
            
            ## set problem to false if muted:
            if pressure_muted is True or muted is True:
                pressure_dict['pressure_problem'] = False
                
            ## compose status message from dict with modified pressure_problem boolean
            status_message = ''
            for ii in pressure_dict:
                status_message = status_message + '\n* ' + str(ii) + ': ' + str(pressure_dict[ii]) + ' '
            
            ## send reply to sender of status request
            bot_handler.send_reply(message, status_message)
            
            ## report problems to stream and subscribers if un-muted:
            if pressure_dict['pressure_problem'] is True and muted is False:
                if pressure_muted is False:
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
            
            ## all clear message to stream and subscribers, if problem resolves itself
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
            
            ## bakeout condition: set problem to false for higher pressure threshold
            try:
                baking = datetime.now() < datetime.strptime(bot_handler.get('bakeout_finish_time'), "%Y-%m-%d %H:%M:%S")
            except:
                baking = False
            if baking is True:
                if pressure_dict['prep_pressure'] < bakeout_pressure_threshold: ## prep pressure threshold
                    pressure_dict['pressure_problem'] = False
                    pressure_dict['baking'] = True
            
            status_message = ''
            for ii in pressure_dict:
                status_message = status_message + '\n* ' + str(ii) + ': ' + str(pressure_dict[ii]) + ' '
            
            msg_dict = dict(
                            type='stream',
                            to='G81 experiments',
                            subject='pressure status',
                            content=status_message,
                            )
            bot_handler.send_message(msg_dict)
            
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
        
        elif command[0] == 'list_subscribers' or command[0] == 'List_subscribers':
            try:
                subscribers = bot_handler.storage.get('subscribers')
                reply_message = ''
                for ii in subscribers:
                    reply_message = reply_message + str(ii) + '\n'
            except:
                reply_message = 'no subscribers list'
            bot_handler.send_reply(message, reply_message)
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
        
        else:
            bot_handler.send_reply(message, HELP_STR)
            return
        
handler_class = PressureStatus