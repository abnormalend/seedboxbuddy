#!/usr/bin/python3

import configparser
import datetime
import time
import logging
import sys
import os
from shutil import copyfile
from rutorrent import RuTorrent
# from pushover import Client

__version__ = "1.1.0"

def str2bool(v):
    """Converts some common strings to a python boolean."""
    return v.lower() in ("yes", "true", "t", "1")

def runningInDocker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )
    # with open('/proc/self/cgroup', 'r') as procfile:
    #     for line in procfile:
    #         fields = line.strip().split('/')
    #         print("docker detector debug:")
    #         print(fields)
    #         if fields[1] == 'docker' or (len(fields) >=3 and 'docker' in fields[2]):
    #             return True
    # return False

def dockerPrepWork():
    foldersToCheck = ['/config', '/download']
    for folder in foldersToCheck:   # We need to make sure that the folders we need exist
        if not os.path.exists(folder):
            print("ERROR: Please create a volume map for " + folder)
            sys.exit(1)
    if not os.path.exists('/config/settings.ini'):  # If a settings file doesn't exist in the mapping copy our sample
        if not os.path.exists('/config/settings.ini.sample'):
            copyfile('/app/settings.ini.sample', '/config/settings.ini.sample')
            print("ERROR: settings.ini.sample created in /config. Rename and add your settings")
            sys.exit(1)
        else:
            print("ERROR: Please rename settings.ini.sample and add your settings")
            sys.exit(1)

# Set up logging
def getLogger(name):
    log_level_info = {'logging.DEBUG': logging.DEBUG, 
                    'logging.INFO': logging.INFO,
                    'logging.WARNING': logging.WARNING,
                    'logging.ERROR': logging.ERROR }
    myLogger = logging.getLogger(name)
    myLogger.setLevel(log_level_info.get(config['settings']['log_level'], logging.INFO))
    if not myLogger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler(sys.stdout)

        handler.setLevel(log_level_info.get(config['settings']['log_level'], logging.INFO))
        handler.setFormatter(formatter)
        myLogger.addHandler(handler)
    return myLogger

# Import settings
def getSettings():
    myConfig = configparser.ConfigParser()
    if docker:
        print("Docker detected")
        myConfig.read(['settings-defaults.ini', '/config/settings.ini'])
    else:
        print("Docker not detected")
        myConfig.read(['settings-defaults.ini', 'settings.ini'])
    # Add trailing / if it's not there already
    if "settings" not in myConfig:
        print("ERROR: Settings file not found.")        # Changed from logger because we want to init this before logger
        exit()
    if '/' not in myConfig['settings']['localSavePath'][-1:]:
        myConfig['settings']['localSavePath'] = myConfig['settings']['localSavePath'] + '/'
    # logger.info("Starting with the following settings:")
    # for key in myConfig['settings']:
    #     logger.info(key + ": " + myConfig['settings'][key])
    return myConfig

def displaySettings():
    logger.debug("Starting with the following settings:")
    for key in config['settings']:
        logger.debug(key + ": " +config['settings'][key])

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

# Check if we're in a container
docker = runningInDocker()      #save this for future reference
if docker:
    print("Running inside Docker was detected")
    dockerPrepWork()

config = getSettings()
logger = getLogger('sbb')
displaySettings()


logger.info("Version: " + __version__)
# Get our config settings
limit_hours = str2bool(config['settings']['limit_hours'])
start_time = config['settings']['start_time'].split(':')
stop_time = config['settings']['stop_time'].split(':')
# Now the main program loop.  If we have support for other servers we can add
#   that here and load something besides rutorrent

if config['settings']['serverType'].lower() == "rutorrent":
    torrentManager = RuTorrent(config, logger)

# Setup pushover
# if config['settings']['pushover_user_key'] is not 'disabled':
#     pushover = Client(config['settings']['pushover_user_key'], api_token=config['settings']['pushover_api_token'])
# else:
#     pushover = False
#

while True:
    if limit_hours:
        if checkDownloadTime():
            timeUntilDownload = datetime.timedelta(minutes=5)
            downloadReport = torrentManager.downloadTorrentsByPattern()
            # logger.info("foo" + downloadReport)
            if downloadReport:
                # We want to keep checking for more downloads while we are in the window, but only log the message if downloads happened
                # if pushover:
                #     logger.info("sending report via pushover: "+ downloadReport)
                #     pushover.send_message(downloadReport, title="Downloads completed", priority=-1, timestamp=True)
                logger.info("Downloads done.  We have " + str(downloadTimeLeft()) + " time left in the download window.  Will check again every " + str(timeUntilDownload))
        else:
            timeUntilDownload = howLongUntilDownloadTime()
            logger.info(f"It is not time to download, so we are going to wait a while.  We need to wait {str(timeUntilDownload)}")
    else:
        downloadReport = torrentManager.downloadTorrentsByPattern()
        if config['settings']['delete_torrents']:
            if torrentManager.get_deletable_torrents():
                logger.info("Found torrents to delete...")
                torrentManager.deleteTorrentsAndFiles()
                logger.info("Finished deleting downloaded torrents.")
            else:
                logger.info("No downloaded torrents found to delete.")

        # Coming soon with pushover support
        # if downloadReport and pushover:
        #     logger.info("sending report via pushover: "+ str(downloadReport))
        #     pushover.send_message(downloadReport, title="Downloads completed", priority=-1, timestamp=True)
        timeUntilDownload = datetime.timedelta(minutes=5)
    time.sleep(timeUntilDownload.total_seconds())  #We're going to wait until download time
