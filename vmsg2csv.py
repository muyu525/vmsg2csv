#!/usr/bin/env python3
# coding=utf8
# -*- coding: utf8 -*-
"""
A script to convert short message backup file in vmsg to csv.
Originally developted by muyu525 (https://github.com/muyu525/vmsg2csv)
Forked by zevanzhao on 2018.02.03
"""

import sys
import quopri
import csv
import random
import re

# vmsg format

# BEGIN:VMSG
# VERSION:1.1
# X-IRMS-TYPE:MSG
# X-MESSAGE-TYPE:DELIVER
# X-MESSAGE-STATUS:READ
# X-MESSAGE-SLOT:0
# X-MESSAGE-LOCKED:UNLOCKED
# BEGIN:VCARD
# VERSION:2.1
# TEL:+86138xxxxxxxx
# END:VCARD
# BEGIN:VBODY
# Date:2014/06/29 09:38:53 GMT
# Subject;ENCODING=QUOTED-PRINTABLE;CHARSET=UTF-8:=30=31=32=33=34=35=36
# END:VBODY
# END:VMSG

# csv format
# id: integer number
# tel: phone number
# type: 'RECEIVED' or 'SEND'
# date: 2015-09-06T20:47:01.573Z
# content:
# end tag: ',y,-1'
#
# example:
# 788,10086,RECEIVED,2013-09-06T20:47:01.573Z,示例内容,y,-1


class VMSG:
    BEGIN = 'BEGIN'
    END = 'END'

    X_MESSAGE_TYPE = 'X-MESSAGE-TYPE'

    TVMSG = 'VMSG'
    TVCARD = 'VCARD'
    TVBODY = 'VBODY'

    X_BOX = 'X-BOX'
    X_MSGBOX = 'X-MSGBOX'
    X_CALLTYPE = 'X-CALLTYPE'
    X_READ = 'X-READ'
    X_SIMID = 'X-SIMID'
    X_LOCKED = 'X-LOCKED'
    X_TYPE = 'X-TYPE'
    X_TYPEEX = 'X-TYPEEX'
    X_KPAS_MSGID = 'X-KPAS_MSGID'
    X_KPAS_SERIAL_NUM = 'X-KPAS_SERIAL_NUM'
    X_SPAM_REPORT = 'X-SPAM_REPORT'
    X_RESERVE_TIME = 'X-RESERVE_TIME'
    X_GROUP_ID = 'X-GROUP_ID'
    X_INSERT_TIME = 'X-INSERT_TIME'
    X_ORIGINAL_ADDR = 'X-ORIGINAL_ADDR'
    X_EXTRA_DATA = 'X-EXTRA_DATA'
    X_SEEN = 'X-SEEN'
    X_VERIFIED = 'X-VERIFIED'

    INBOX = 'INBOX'
    TDELIVER = 'DELIVER'
    TSUBMIT = 'SUBMIT'

    TTEL = 'TEL'
    TDATE = 'Date'
    TSUBJECT = 'Subject'

    def __init__(self):
        pass

def build_from_message(fvmsg, fcsv):
    with open(fvmsg, 'r') as f:
        v_l = [] # result
        stack = []
        for line in f:
            line = line.strip()
            if line.startswith(VMSG.BEGIN):
                process_start_tag(line, stack, v_l)
            elif line.startswith(VMSG.END):
                process_end_tag(line, stack, v_l)
            else:
                process_attribute(line, stack, v_l)

    with open(fcsv, 'w') as fout:
        writer = csv.writer(fout, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        item_id = 1
        for item in v_l:
            row = process_item(item_id, item)
            #print("Writing row %s" %(row))
            writer.writerow(row)
            item_id += 1


def process_item(item_id, item):
    row = list()

    row.append(item_id)
    row.append(item['tel'])
    row.append(item['type'])
    row.append(item['date'])
    row.append(item['content'])
    row.append(item['status'])
    row.append(item['end'])

    return row


def process_start_tag(stream, stack, v):
    tag = stream[6:]
    #print('process_start_tag:', tag)
    if len(tag) == 0:
        raise ValueError

    #print('pushing:', tag)
    stack.append(tag)

    if tag == VMSG.TVMSG:
        item = {'status': 'y', 'end': '-1'}
        v.append(item)


def process_end_tag(stream, stack, v):
    tag = stream[4:]
    #print('process_end_tag:', tag)
    if len(tag) == 0:
        raise ValueError

    if tag != stack[-1]:
        raise ValueError

    stack.pop()
    #print('poping:', stream)

    if tag == VMSG.TVMSG:
        # decode content here
        item = v[-1]
        if item.get('content'):
            item['content'] = decode_subject(item['content'])
        else:
            print('Error: Subject not found')
            sys.exit(1)

def process_attribute(stream, stack, v):
    if len(stack) > 0:
        tag = stack[-1]
        if tag == VMSG.TVMSG:
            if stream.startswith(VMSG.X_MESSAGE_TYPE):
                process_message_type(stream, v)
        if tag == VMSG.TVCARD:
            if stream.startswith(VMSG.TTEL):
                process_tel(stream, v)
        elif tag == VMSG.TVBODY:
            if stream.startswith(VMSG.X_BOX):
                process_box(stream, v)
            elif stream.startswith(VMSG.X_READ):
                pass
            elif stream.startswith(VMSG.X_SIMID):
                pass
            elif stream.startswith(VMSG.X_LOCKED):
                pass
            elif stream.startswith(VMSG.X_TYPE):
                pass
            elif stream.startswith(VMSG.TDATE):
                process_date(stream, v)
            elif stream.startswith(VMSG.TSUBJECT):
                process_subject(stream, v)
            else:
                i = stream.find(':')
                if i == -1: # not a tag, continue subject
                    process_continue_subject(stream, v)
                else: # unkown tag
                    pass


def process_message_type(stream, v):
    type = stream[15:]

    if type == VMSG.TSUBMIT:
        type = 'SENT'
    else:
        type = 'RECEIVED'

    item = v[-1]
    item['type'] = type

def process_box(stream, v):
    type = stream[6:]

    if type == VMSG.INBOX:
        type = 'RECEIVED'
    else:
        type = 'SENT'

    item = v[-1]
    item['type'] = type


def process_tel(stream, v):
    tel = stream[4:]
    if tel.startswith("+86"):
        tel = tel.replace("+86", "")

    item = v[-1]
    item['tel'] = tel


def process_date(stream, v):
    date = stream[5:24]
    date = date.replace(' ', 'T')
    date = date.replace('/', '-')

    r = '%03d' % (random.randint(0, 999))

    date = date + '.' + r + 'Z'

    item = v[-1]
    item['date'] = date


def process_subject(stream, v):
    s = stream.split(':', 1)
    content = s[-1]

    item = v[-1]
    item['content'] = content


def process_continue_subject(stream, v):
    item = v[-1]
    if item.get('content'):
        content = stream

        item['content'] = item['content'] + content

def decode_subject(content):
    #b = bytearray.fromhex(item['content'])
    #replace "==" by "="
    content = re.sub("==", "=",content)
    #print("Decoding contents: %s" %(content))
    #quopri should be used here.
    result = quopri.decodestring(content).decode("utf-8")
    #print("Results: %s" %result)
    return str(result)

if '__main__' == __name__:
    fvmsg = sys.argv[1]
    fcsv = sys.argv[2]

    build_from_message(fvmsg, fcsv)
