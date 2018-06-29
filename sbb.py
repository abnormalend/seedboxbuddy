#!/usr/bin/python

import configparser
import datetime
import time
import logging
from rutorrent import rutorrent

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

# Set up logging
logger = logging.getLogger('seedBoxBuddy')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Get our config settings
config = configparser.ConfigParser()
config.read(['settings-defaults.ini', 'settings.ini'])
limit_hours = str2bool(config['settings']['limit_hours'])
start_time = config['settings']['start_time'].split(':')
stop_time = config['settings']['stop_time'].split(':')

# A few functions to handle the time
def checkDownloadTime():
    logger.info("Checking if it's time to run downloads")
    now = datetime.datetime.now()
    starting_time = now.replace(hour=int(start_time[0]), minute=int(start_time[1]), second=0, microsecond=0)
    stopping_time = now.replace(hour=int(stop_time[0]), minute=int(stop_time[1]), second=0, microsecond=0)
    starting_time, stopping_time = handleOvernightDownloadTime(starting_time, stopping_time)
    if (now > starting_time) and (now < stopping_time):
        logger.info("It is download time")
        return True
    else:
        logger.info("Nope, not download time")
        return False

def handleOvernightDownloadTime(starting_time, stopping_time):
    now = datetime.datetime.now()
    if stopping_time < starting_time:
        logger.debug("download goes overnight")
        if (starting_time < now) and (stopping_time < now):
            logger.debug("add 1 day to the stopping time")
            stopping_time = stopping_time + datetime.timedelta(days=1)
        if (starting_time > now) and (stopping_time > now):
            logger.debug("subtract 1 day from the starting time")
            starting_time = starting_time - datetime.timedelta(days=1)
    return starting_time, stopping_time

def downloadTimeLeft():
    if checkDownloadTime():
        now = datetime.datetime.now()
        starting_time = now.replace(hour=int(start_time[0]), minute=int(start_time[1]), second=0, microsecond=0)
        stopping_time = now.replace(hour=int(stop_time[0]), minute=int(stop_time[1]), second=0, microsecond=0)
        starting_time, stopping_time = handleOvernightDownloadTime(starting_time, stopping_time)
        return stopping_time - now

# Now the main program loop.  If we have support for other servers we can add
#   that here and load something besides rutorrent

if config['settings']['serverType'].lower() == "rutorrent":
    torrentManager = rutorrent(config)

while True:
    if limit_hours:
        if checkDownloadTime():
            torrentManager.downloadTorrentsByPattern()
            logger.info("Downloads done")
            logger.info(str(downloadTimeLeft()))
        else:
            logger.debug("It's not time, so we're going to wait")
    else:
        torrentManager.downloadTorrentsByPattern()
    time.sleep(60)  #We're going to wait for one minute before starting over
