#!/usr/bin/env python3
#
# Script: smtools.py
#
# (c) 2013 SUSE Linux GmbH, Germany.
# GNU Public License. No warranty. No Support (only from SUSE Consulting)
#
# Version: 2017-10-11
#
# Created by: SUSE Michael Brookhuis,
#
# Description: This script contains standard function that can be used in several other scripts
#
# Releases:
# 2017-10-14 M.Brookhuis - initial release.
# 2018-11-15 M.Brookhuis - Moved to python3.
#                        - Moved config to YAML
#

"""This library contains functions used in other modules"""

from email.mime.text import MIMEText
import xmlrpc.client
import logging
import os
import sys
import datetime
import smtplib
import yaml


ERROR_FOUND = False
ERROR_TEXT = ""
HOSTNAME = ""
LOGGER = ""

if not os.path.isfile(os.path.dirname(__file__)+"/configsm.yaml"):
    print("ERROR: configsm.yaml doesn't exist. Please create file")
    sys.exit(1)
else:
    CONFIGSM = yaml.load(open(os.path.dirname(__file__)+'/configsm.yaml'))

####################################sm#########
#
# Functions
#

def set_logging(host_name="", file_based=False):
    """Set Logging"""
    global LOGGER
    log_dir = CONFIGSM['dirs']['log_dir']+"/"+sys.argv[0].split('/')[-1].split('.')[0]
    if file_based:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_name = log_dir+"/"+host_name+".log"
    else:
        if not os.path.exists(CONFIGSM['dirs']['log_dir']):
            os.makedirs(CONFIGSM['dirs']['log_dir'])
        log_name = log_dir+".log"
    logging.basicConfig(filename=log_name,
                        filemode='a',
                        format='%(asctime)s : %(name)s : %(levelname)s - %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        level=logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logging.getLogger('').addHandler(console)
    LOGGER = logging.getLogger(host_name)

def suman_login():
    """Log in to SUSE Manager Server"""
    clt = xmlrpc.client.Server("http://"+CONFIGSM['suman']['server']+"/rpc/api")
    try:
        ses = clt.auth.login(CONFIGSM['suman']['user'], CONFIGSM['suman']['password'])
    except xmlrpc.client.Fault:
        LOGGER.error("| %s | Unable to login to SUSE Manager server" % HOSTNAME)
        sys.exit(1)
    return clt, ses

def suman_logout(clt, ses):
    """Logout from SUSE Manager Server"""
    global ERROR_FOUND
    global ERROR_TEXT
    try:
        clt.auth.logout(ses)
    except xmlrpc.client.Fault:
        LOGGER.error("| %s | Unable to logout from SUSE Manager" % HOSTNAME)
        ERROR_FOUND = True
        ERROR_TEXT = ERROR_TEXT+"\n Problem closing connection to SUSE Manager"

def minor_error(errtxt):
    """Log minor error"""
    global ERROR_FOUND
    global ERROR_TEXT
    ERROR_FOUND = True
    LOGGER.warning("| %s" % (errtxt))
    ERROR_TEXT = ERROR_TEXT+"\n"+errtxt

def fatal_error(errtxt, return_code=1):
    """Log fatal error and close program"""
    global ERROR_FOUND
    global ERROR_TEXT
    ERROR_FOUND = True
    ERROR_TEXT = ERROR_TEXT+"\n"+errtxt
    LOGGER.error("| %s" % (errtxt))
    close_program(return_code)

def log_info(txt):
    """Log info text"""
    LOGGER.info("| %s" % (txt))

def log_error(txt):
    """Log error text"""
    LOGGER.error("| %s" % (txt))


def send_mail():
    """Send Mail"""
    global ERROR_FOUND
    global ERROR_TEXT
    script = os.path.basename(sys.argv[0])
    try:
        smtp_connection = smtplib.SMTP(CONFIGSM['smtp']['server'])
    except xmlrpc.client.Fault:
        print("error when sending mail")
    #smtp_connection.set_debuglevel(1)
    txt = ("Dear admin,\n\nThe job %s has run today at %s.\n\nUnfortunately there have been some errors.\n\nPlease see the following list:\n" % (script, datetime.datetime.now()))
    ERROR_TEXT = txt+ERROR_TEXT
    msg = MIMEText(ERROR_TEXT)
    sender = CONFIGSM['smtp']['sender']
    recipients = CONFIGSM['smtp']['receivers']
    msg['Subject'] = ("[%s] on server %s from %s has errors" % (script, HOSTNAME, datetime.datetime.now()))
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    try:
        smtp_connection.sendmail(sender, recipients, msg.as_string())
    except:
        logger.error("sending mail failed")

def set_hostname(host_name):
    """Set hostnam for global use"""
    global HOSTNAME
    HOSTNAME = host_name

def close_program(return_code=0):
    """Close program and send mail if there is an error"""
    logging.info("| Finished %s" % (datetime.datetime.now()))
    if ERROR_FOUND:
        if CONFIGSM['smtp']['sendmail']:
            send_mail()
    sys.exit(return_code)
