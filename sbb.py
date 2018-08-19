#!/usr/bin/python3

from configparser import SafeConfigParser
import datetime
import time
import logging
import sys
import os
from shutil import copyfile
from rutorrent import rutorrent

__version__ = "1.0.0"

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def runningInDocker():
    with open('/proc/self/cgroup', 'r') as procfile:
        for line in procfile:
            fields = line.strip().split('/')
            if fields[1] == 'docker':
                return True
    return False

def dockerPrepWork():
    foldersToCheck = ['/config', '/download']
    for folder in foldersToCheck:   # We need to make sure that the folders we need exist
        if not os.path.exists(folder):
            logger.error("Please create a volume map for " + folder)
            sys.exit(1)
    logger.debug("checking to see if settings file exists")
    if not os.path.exists('/config/settings.ini'):  # If a settings file doesn't exist in the mapping copy our sample
        if not os.path.exists('/config/settings.ini.sample'):
            copyfile('/app/settings.ini.sample', '/config/settings.ini.sample')
            logger.error("settings.ini.sample created in /config. Rename and add your settings")
            sys.exit(1)
        else:
            logger.error("Please rename settings.ini.sample and add your settings")
            sys.exit(1)

# Set up logging
def getLogger(name):
    myLogger = logging.getLogger(name)
    myLogger.setLevel(logging.DEBUG)
    if not myLogger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        myLogger.addHandler(handler)
    return myLogger

# Import settings
def getSettings():
    myConfig = SafeConfigParser()
    if docker:
        myConfig.read(['settings-defaults.ini', '/config/settings.ini'])
    else:
        myConfig.read(['settings-defaults.ini', 'settings.ini'])
    # Add trailing / if it's not there already
    if '/' not in myConfig.get('settings','localSavePath')[-1:]:
        myConfig['settings']['localSavePath'] = myConfig['settings']['localSavePath'] + '/'
    logger.info("Starting with the following settings:")
    for key in myConfig['settings']:
        logger.info(key + ": " + myConfig['settings'][key])
    return myConfig

# A few functions to handle the time
def checkDownloadTime():
    logger.debug("Checking if it's time to run downloads")
    now = datetime.datetime.now()
    starting_time = now.replace(hour=int(start_time[0]), minute=int(start_time[1]), second=0, microsecond=0)
    stopping_time = now.replace(hour=int(stop_time[0]), minute=int(stop_time[1]), second=0, microsecond=0)
    starting_time, stopping_time = handleOvernightDownloadTime(starting_time, stopping_time)
    if (now > starting_time) and (now < stopping_time):
        logger.debug("It is download time")
        return True
    else:
        logger.debug("Nope, not download time")
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

def howLongUntilDownloadTime():
    if not checkDownloadTime():
        now = datetime.datetime.now()
        starting_time = now.replace(hour=int(start_time[0]), minute=int(start_time[1]), second=0, microsecond=0)
        stopping_time = now.replace(hour=int(stop_time[0]), minute=int(stop_time[1]), second=0, microsecond=0)
        if now > starting_time:
            logger.debug("add 1 day to the starting time")
            starting_time = starting_time + datetime.timedelta(days=1)
        # starting_time, stopping_time = handleOvernightDownloadTime(starting_time, stopping_time)
        return starting_time - now


logger = getLogger('sbb')
# Check if we're in a container
docker = runningInDocker()      #save this for future reference
if docker:
    logger.info("Running inside Docker was detected")
    dockerPrepWork()

logger.info("Version: " + __version__)
# Get our config settings
config = getSettings()
limit_hours = str2bool(config['settings']['limit_hours'])
start_time = config['settings']['start_time'].split(':')
stop_time = config['settings']['stop_time'].split(':')
# Now the main program loop.  If we have support for other servers we can add
#   that here and load something besides rutorrent

if config['settings']['serverType'].lower() == "rutorrent":
    torrentManager = rutorrent(config, logger)
    logger.info("rutorrent class version: " + torrentManager.getVersion())

# if config['settings']['autolabel_enabled'] == 'True':
#     for name, value in config.items('autolabel'):
#         print('  %s = %s' % (name, value))
#     # torrentManager.autoLabelTorrents()

while True:
    if limit_hours:
        if checkDownloadTime():
            timeUntilDownload = datetime.timedelta(minutes=5)
            if torrentManager.downloadTorrentsByPattern():
                # We want to keep checking for more downloads while we are in the window, but only log the message if downloads happened
                logger.info("Downloads done.  We have " + str(downloadTimeLeft()) + " time left in the download window.  Will check again every " + str(timeUntilDownload))
        else:
            timeUntilDownload = howLongUntilDownloadTime()
            logger.info("It is not time to download, so we are going to wait a while.  We need to wait " + str(timeUntilDownload))
    else:
        torrentManager.downloadTorrentsByPattern()
        timeUntilDownload = datetime.timedelta(minutes=5)
    time.sleep(timeUntilDownload.total_seconds())  #We're going to wait until download time
