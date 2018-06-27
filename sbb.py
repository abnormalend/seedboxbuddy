#!/usr/bin/python

import configparser             #MIT
import datetime                 #zope
import time
# import json
# import requests
import logging
# from paramiko import SSHClient
# from scp import SCPClient
from rutorrent import rutorrent

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

# logger.basicConfig(level=logging.INFO)

logger = logging.getLogger('seedBoxBuddy')

logger.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

config = configparser.ConfigParser()
config.read('settings.ini')
# ignoreLabels = config['settings']['ignoreLabels'].split(',')
# maxSize = int(config['settings']['maxSize'])
limit_hours = str2bool(config['settings']['limit_hours'])
start_time = config['settings']['start_time'].split(':')
stop_time = config['settings']['stop_time'].split(':')
# logger.debug(ignoreLabels)

# myTorrents = {}

# def getFileWithSCP(file, recursive, label):
#     ssh = SSHClient()
#     ssh.load_system_host_keys()
#     ssh.connect(config['settings']['myServer'], username=config['settings']['myUsername'], password=config['settings']['myPassword'])
#
#     # Where are we putting this?  Make the folder if it doesn't already exist
#     downloadLocation = config['settings']['localSavePath'] + label + "/"
#     if not os.path.exists(downloadLocation):
#         try:
#             os.makedirs(downloadLocation)
#         except OSError as e:
#             if e.errno != errno.EEXIST:
#                 raise
#
#     # SCPCLient takes a paramiko transport as an argument
#     scp = SCPClient(ssh.get_transport())
#     # try:
#     scp.get(file,config['settings']['localSavePath'] + label + "/",recursive=recursive)
#     return True

    # except:
        # logger.error("Uh oh!")
        # if e is defined:
        #     logger.error(e)
    # except ConnectionError:
    #     logger.error("Connection error has occurred")
    #     logger.error(e)
        # return False

# def downloadAndLabelByHash(hash,multi_file,label):
#     setLabel(hash,'downloading')
#     if  getFileWithSCP(myTorrents[hash]['file_path'], multi_file, label):
#         setLabel(hash,'downloaded')
#         del myTorrents[hash]

# def getTorrents():
#     url = "http://" + config['settings']['myServer'] + config['settings']['myruTorrentPath'] + "/httprpc/action.php"
#     payload = {'mode': 'list'}
#     headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
#     try:
#         response = requests.request("POST", url, data=payload, headers=headers, auth=(config['settings']['myUsername'],config['settings']['myPassword']))
#         json_data = response.json()
#     except:
#         logger.error("something has gone wrong")
#     i = 0
#     for item in json_data["t"].items():
#         if item[1][14] not in ignoreLabels and int(item[1][5]) < maxSize and int(item[1][19]) is 0:
#             myName = item[1][4]
#             myLabel = item[1][14]
#             mySize = int(item[1][5])
#             myFilePath =  item[1][25]
#             myCreated = item[1][26]
#             myMultiFile =  bool(int(item[1][33]))
#             myTorrents[item[0]] = {
#                 'name': myName,
#                 'label': myLabel,
#                 'size': mySize,
#                 'file_path': myFilePath,
#                 'multi_file': myMultiFile,
#                 'created': myCreated
#                 }


# def setLabel(hash, label):
#     url = "http://" + config['settings']['myServer'] + config['settings']['myruTorrentPath'] + "/httprpc/action.php"
#     payload = {'mode': 'setlabel', 'hash': hash, 's': 'label', 'v':	label }
#     headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
#
#     response = requests.request("POST", url, data=payload, headers=headers, auth=(config['settings']['myUsername'],config['settings']['myPassword']))
#     json_data = response.json()


# def getTorrentByPattern():
#     """Return the hash of the smallest or largest torrent in the list."""
#     myHash = ""
#     myAge = 0
#     mySize = 0
#     if 'newest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             if mySize > item['created'] or myHash == "":
#                 mySize = item['created']
#                 myHash = hash
#         return myHash
#     if 'oldest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             logger.debug(item['size'])
#             if mySize < item['created'] or myHash == "":
#                 logger.debug(item['name'])
#                 mySize = item['size']
#                 myHash = hash
#         return myHash
#     if 'smallest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             logger.debug(item['size'])
#             if mySize > item['size'] or myHash == "":
#                 logger.debug(item['name'])
#                 mySize = item['size']
#                 myHash = hash
#         return myHash
#     if 'largest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             logger.debug(item['size'])
#             if mySize < item['size'] or myHash == "":
#                 logger.debug(item['name'])
#                 mySize = item['size']
#                 myHash = hash
#         return myHash
#     return False  #Something went wrong
#
# def getTorrentBySize():
#     """Return the hash of the smallest or largest torrent in the list."""
#     myHash = ""
#     mySize = 0
#     if 'smallest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             logger.info(item['size'])
#             if mySize > item['size'] or myHash == "":
#                 logger.info(item['name'])
#                 mySize = item['size']
#                 myHash = hash
#         return myHash
#     if 'largest' in config['settings']['downloadPattern']:
#         for hash, item in myTorrents.items():
#             logger.debug(item['size'])
#             if mySize < item['size'] or myHash == "":
#                 logger.debug(item['name'])
#                 mySize = item['size']
#                 myHash = hash
#         return myHash
#     return False  #Something went wrong

# def downloadTorrentsBySize():
#     getTorrents()
#     while myTorrents:
#         nextTorrent = getTorrentBySize()
#         logger.info("Download Queue Size: " + str(len(myTorrents)))
#         logger.info("Downloading " + myTorrents[nextTorrent]['name'] + "  size: " + "{:,}".format(myTorrents[nextTorrent]['size']))
#         downloadAndLabelByHash(nextTorrent, myTorrents[nextTorrent]['multi_file'],myTorrents[nextTorrent]['label'] )
#         logger.info("Going to sleep for " + config['settings']['delayBetweenDownloads'] + " seconds")
#         time.sleep(int(config['settings']['delayBetweenDownloads']))
#         getTorrents()
#     logger.info("Finished with all Downloads!")

# def downloadTorrentsByPattern():
#     getTorrents()
#     while myTorrents:
#         nextTorrent = getTorrentByPattern()
#         logger.info("Download Queue Size: " + str(len(myTorrents)))
#         logger.info("Downloading " + myTorrents[nextTorrent]['name'] + "  size: " + "{:,}".format(myTorrents[nextTorrent]['size']))
#         downloadSize = myTorrents[nextTorrent]['size']
#         preDownloadTime = time.time()
#         downloadAndLabelByHash(nextTorrent, myTorrents[nextTorrent]['multi_file'],myTorrents[nextTorrent]['label'] )
#         postDownloadTime = time.time()
#         downloadTime = postDownloadTime - preDownloadTime
#         logger.info("Download took " + str(downloadTime) + " seconds")
#         logger.info("Download Speed: " +  "{:,}".format(round((downloadSize/downloadTime)/1024)) + " kilobytes/second")
#         logger.info("Going to sleep for " + config['settings']['delayBetweenDownloads'] + " seconds")
#         if len(myTorrents) > 0:
#             time.sleep(int(config['settings']['delayBetweenDownloads']))
#             getTorrents()
#     logger.info("Finished with all Downloads!")


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
        # logger.info("stop time: " + str(stopping_time))

        return stopping_time - now

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
