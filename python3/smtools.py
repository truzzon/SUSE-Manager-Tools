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
# coding: utf-8

"""
This library contains functions used in other modules
"""

from email.mime.text import MIMEText
import xmlrpc.client
import logging
import os
import sys
import datetime
import smtplib
import yaml

def load_yaml(stream):
    """
    Load YAML data.
    """
    loader = yaml.FullLoader(stream)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


if not os.path.isfile(os.path.dirname(__file__) + "/configsm.yaml"):
    print("ERROR: configsm.yaml doesn't exist. Please create file")
    sys.exit(1)
else:
    with open(os.path.dirname(__file__) + '/configsm.yaml') as h_cfg:
        CONFIGSM = load_yaml(h_cfg)


class SMTools:
    """
    Class to define needed tools.
    """
    error_text = ""
    error_found = False
    hostname = ""
    client = ""
    session = ""

    def __init__(self, hostname="", hostbased=False):
        """
        Constructor.
        """
        self.hostname = hostname
        self.hostbased = hostbased
        log_dir = os.path.join(CONFIGSM['dirs']['log_dir'], __file__.split(".")[0])
        if self.hostbased:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_name = os.path.join(log_dir, self.hostname + ".log")
        else:
            if not os.path.exists(CONFIGSM['dirs']['log_dir']):
                os.makedirs(CONFIGSM['dirs']['log_dir'])
            log_name = os.path.join(log_dir, "smtools.log")
        logging.basicConfig(filename=log_name,
                            filemode='a',
                            format='%(asctime)s : %(levelname)s  %(message)s',
                            datefmt='%d-%m-%Y %H:%M:%S',
                            level=logging.DEBUG)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(console)
        logging.getLogger(self.hostname)

    def minor_error(self, errtxt):
        """
        Print minor error.
        """
        self.error_text += errtxt
        self.error_text += "\n"
        self.error_found = True
        logging.warning(f"| {errtxt}")

    def fatal_error(self, errtxt, return_code=1):
        """
        Log fatal error and exit program.
        """
        self.error_text += errtxt
        self.error_text += "\n"
        self.error_found = True
        logging.error(f"| {errtxt}")
        self.close_program(return_code)

    @staticmethod
    def log_info(errtxt):
        """
        Log info text.
        """
        logging.info(f"| {errtxt}")

    @staticmethod
    def log_error(errtxt):
        """
        Log error text.
        """
        logging.error(f"| {errtxt}")

    def send_mail(self):
        """
        Send Mail.
        """
        script = os.path.basename(sys.argv[0])
        # noinspection PyBroadException
        try:
            smtp_connection = smtplib.SMTP(CONFIGSM['smtp']['server'])
        except Exception:
            self.fatal_error("error when sending mail")
        datenow = datetime.datetime.now()
        txt = f"Dear admin,\n\nThe job {script} has run today at {datenow}."
        txt += "\n\nUnfortunately there have been some error\n\nPlease see the following list:\n"
        txt += self.error_text
        msg = MIMEText(txt)
        sender = CONFIGSM['smtp']['sender']
        recipients = CONFIGSM['smtp']['receivers']
        msg['Subject'] = f"[{script}] on server {self.hostname} )from {datenow} has errors"
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)
        # noinspection PyBroadException
        try:
            # noinspection PyUnboundLocalVariable
            smtp_connection.sendmail(sender, recipients, msg.as_string())
        except Exception:
            logging.error("sending mail failed")

    def set_hostname(self, host_name):
        """
        Set hostnam for global use.
        """
        self.hostname = host_name

    def close_program(self, return_code=0):
        """Close program and send mail if there is an error"""
        logging.info(f"| Finished {datetime.datetime.now()}")
        if self.error_found and CONFIGSM['smtp']['sendmail']:
            self.send_mail()
        sys.exit(return_code)

    def suman_login(self):
        """
        Log in to SUSE Manager Server.
        """
        self.client = xmlrpc.client.Server("http://" + CONFIGSM['suman']['server'] + "/rpc/api")
        try:
            self.session = self.client.auth.login(CONFIGSM['suman']['user'], CONFIGSM['suman']['password'])
        except xmlrpc.client.Fault:
            self.fatal_error("| %s | Unable to login to SUSE Manager server" % CONFIGSM['suman']['server'])

    def suman_logout(self):
        """
        Logout from SUSE Manager Server.
        """
        try:
            self.client.auth.logout(self.session)
        except xmlrpc.client.Fault:
            self.fatal_error("| %s | Unable to logout from SUSE Manager" % CONFIGSM['suman']['server'])
