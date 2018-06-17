#!/usr/bin/python

import configparser
import datetime
import time
import json
import requests
import logging
from paramiko import SSHClient
from scp import SCPClient

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('settings.ini')
ignoreLabels = config['settings']['ignoreLabels'].split(',')
maxSize = int(config['settings']['maxSize'])
limit_hours = bool(config['settings']['limit_hours'])
start_time = config['settings']['start_time'].split(':')
stop_time = config['settings']['stop_time'].split(':')
logging.debug(ignoreLabels)

myTorrents = {}

def getFileWithSCP(file, recursive):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(config['settings']['myServer'], username=config['settings']['myUsername'], password=config['settings']['myPassword'])

    # SCPCLient takes a paramiko transport as an argument
    scp = SCPClient(ssh.get_transport())
    try:
        scp.get(file,config['settings']['localSavePath'],recursive=recursive)
        return True
    except SCPException:
        return False

def downloadAndLabelByHash(hash,multi_file):
    setLabel(hash,'downloading')
    if  getFileWithSCP(myTorrents[hash]['file_path'], multi_file):
        setLabel(hash,'downloaded')
        del myTorrents[hash]

def getTorrents():
    url = "http://" + config['settings']['myServer'] + config['settings']['myruTorrentPath'] + "/httprpc/action.php"
    payload = {'mode': 'list'}
    headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}

    response = requests.request("POST", url, data=payload, headers=headers, auth=(config['settings']['myUsername'],config['settings']['myPassword']))
    json_data = response.json()
    i = 0
    for item in json_data["t"].items():
        if item[1][14] not in ignoreLabels and int(item[1][5]) < maxSize:
            myName = item[1][4]
            myLabel = item[1][14]
            mySize = int(item[1][5])
            myFilePath =  item[1][25]
            myCreated = item[1][26]
            myMultiFile =  bool(int(item[1][33]))
            myTorrents[item[0]] = {
                'name': myName,
                'label': myLabel,
                'size': mySize,
                'file_path': myFilePath,
                'multi_file': myMultiFile,
                'created': myCreated
                }


def setLabel(hash, label):
    url = "http://" + config['settings']['myServer'] + config['settings']['myruTorrentPath'] + "/httprpc/action.php"
    payload = {'mode': 'setlabel', 'hash': hash, 's': 'label', 'v':	label }
    headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}

    response = requests.request("POST", url, data=payload, headers=headers, auth=(config['settings']['myUsername'],config['settings']['myPassword']))
    json_data = response.json()


def getTorrentByPattern():
    """Return the hash of the smallest or largest torrent in the list."""
    myHash = ""
    myAge = 0
    mySize = 0
    if 'newest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            if mySize > item['created'] or myHash == "":
                mySize = item['created']
                myHash = hash
        return myHash
    if 'oldest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            logging.debug(item['size'])
            if mySize < item['created'] or myHash == "":
                logging.debug(item['name'])
                mySize = item['size']
                myHash = hash
        return myHash
    if 'smallest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            logging.debug(item['size'])
            if mySize > item['size'] or myHash == "":
                logging.debug(item['name'])
                mySize = item['size']
                myHash = hash
        return myHash
    if 'largest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            logging.debug(item['size'])
            if mySize < item['size'] or myHash == "":
                logging.debug(item['name'])
                mySize = item['size']
                myHash = hash
        return myHash
    return False  #Something went wrong

def getTorrentBySize():
    """Return the hash of the smallest or largest torrent in the list."""
    myHash = ""
    mySize = 0
    if 'smallest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            logging.info(item['size'])
            if mySize > item['size'] or myHash == "":
                logging.info(item['name'])
                mySize = item['size']
                myHash = hash
        return myHash
    if 'largest' in config['settings']['downloadPattern']:
        for hash, item in myTorrents.items():
            logging.debug(item['size'])
            if mySize < item['size'] or myHash == "":
                logging.debug(item['name'])
                mySize = item['size']
                myHash = hash
        return myHash
    return False  #Something went wrong

def downloadTorrentsBySize():
    getTorrents()
    while myTorrents:
        nextTorrent = getTorrentBySize()
        logging.info("Download Queue Size: " + str(len(myTorrents)))
        logging.info("Downloading " + myTorrents[nextTorrent]['name'] + "  size: " + "{:,}".format(myTorrents[nextTorrent]['size']))
        downloadAndLabelByHash(nextTorrent, myTorrents[nextTorrent]['multi_file'])
        logging.info("Going to sleep for " + config['settings']['delayBetweenDownloads'] + " seconds")
        time.sleep(int(config['settings']['delayBetweenDownloads']))
        getTorrents()
    logging.info("Finished with all Downloads!")

def downloadTorrentsByPattern():
    getTorrents()
    while myTorrents:
        nextTorrent = getTorrentByPattern()
        logging.info("Download Queue Size: " + str(len(myTorrents)))
        logging.info("Downloading " + myTorrents[nextTorrent]['name'] + "  size: " + "{:,}".format(myTorrents[nextTorrent]['size']))
        downloadSize = myTorrents[nextTorrent]['size']
        preDownloadTime = time.time()
        downloadAndLabelByHash(nextTorrent, myTorrents[nextTorrent]['multi_file'])
        postDownloadTime = time.time()
        downloadTime = postDownloadTime - preDownloadTime
        logging.info("Download took " + str(downloadTime) + " seconds")
        logging.info("Download Speed: " +  "{:,}".format(round((downloadSize/downloadTime)/1024)) + " kilobytes/second")
        logging.info("Going to sleep for " + config['settings']['delayBetweenDownloads'] + " seconds")
        if len(myTorrents) > 0:
            time.sleep(int(config['settings']['delayBetweenDownloads']))
            getTorrents()
    logging.info("Finished with all Downloads!")


def checkDownloadTime():
    logging.info("Checking if it's time to run downloads")
    now = datetime.datetime.now()
    starting_time = now.replace(hour=int(start_time[0]), minute=int(start_time[1]), second=0, microsecond=0)
    stopping_time = now.replace(hour=int(stop_time[0]), minute=int(stop_time[1]), second=0, microsecond=0)
    if stopping_time < starting_time:
        logging.debug("download goes overnight")
        if (starting_time < now) and (stopping_time < now):
            logging.debug("add 1 day to the stopping time")
            stopping_time = stopping_time + datetime.timedelta(days=1)
        if (starting_time > now) and (stopping_time > now):
            logging.debug("subtract 1 day from the starting time")
            starting_time = starting_time - datetime.timedelta(days=1)
    if (now > starting_time) and (now < stopping_time):
        logging.info("It is download time")
        return True
    else:
        logging.info("Nope, not download time")
        return False

for hash, item in myTorrents.items():
    logging.debug(hash)
    logging.debug("name: " + item['name'])
    logging.debug("label: " + item['label'])
    logging.debug("size: " + "{:,}".format(item['size']))
    logging.debug

while True:
    if limit_hours:
        if checkDownloadTime():
            downloadTorrentsByPattern()
        else:
            logging.debug("It's not time, so we're going to wait")
            time.sleep(60)  #We're going to wait for one minute since it isn't time yet
    else:
        downloadTorrentsByPattern()

#     raise ConnectionError(e, request=request)
# requests.exceptions.ConnectionError: HTTPConnectionPool(host='3-22heathrow.pulse                                            dmedia.com', port=80): Max retries exceeded with url: /user-skinemax/rutorrent/p                                            lugins/httprpc/action.php (Caused by NewConnectionError('<urllib3.connection.HTT                                            PConnection object at 0x7f03ef80e8d0>: Failed to establish a new connection: [Er                                            rno -3] Temporary failure in name resolution',))
