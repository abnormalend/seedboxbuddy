"""Manges a connection to ruTorrent."""
import logging
import requests
import time
import os
import json
import shutil
import paramiko
from paramiko import SSHClient
from scp import SCPClient

class rutorrent:
    """Functions and things for managing an rutorrent server."""

    def __init__(self, config, logger):

        # self.logger = logging.getLogger("sbb."+__name__)
        self.logger = logger

        self.myTorrents = {}
        self.server =config['settings']['myServer']
        self.ruTorrentPath = config['settings']['myTorrentPath']
        self.username = config['settings']['myUsername']
        self.password = config['settings']['myPassword']
        self.ignoreLabels = config['settings']['ignoreLabels'].split(',')
        self.maxSize = int(config['settings']['maxSize'])
        self.pattern = config['settings']['downloadPattern']
        self.localSavePath = config['settings']['localSavePath']
        self.duplicate_action = config['settings']['duplicate_action'].lower()
        self.grabTorrents()

    def grabTorrents(self):
        url = "http://" + self.server + self.ruTorrentPath + "/httprpc/action.php"
        payload = {'mode': 'list'}
        headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
        try:
            response = requests.request("POST", url, data=payload, headers=headers, auth=(self.username,self.password))
            json_data = response.json()
        except Exception as e:
            self.logger.error("something has gone wrong")
            self.logger.error(e)
        i = 0
        for item in json_data["t"].items():
            if item[1][14] not in self.ignoreLabels and int(item[1][5]) < self.maxSize and int(item[1][19]) is 0:
                myName = item[1][4]
                myLabel = item[1][14]
                mySize = int(item[1][5])
                myFilePath =  item[1][25]
                myCreated = item[1][26]
                myMultiFile =  bool(int(item[1][33]))
                self.myTorrents[item[0]] = {
                    'name': myName,
                    'label': myLabel,
                    'size': mySize,
                    'file_path': myFilePath,
                    'multi_file': myMultiFile,
                    'created': myCreated
                    }

    def getAllTorrents(self):
        self.logger.info("Printing all torrent details")
        print self.myTorrents
        for hash, item in self.myTorrents.items():
            self.logger.info(hash)
            self.logger.info("name: " + item['name'])
            self.logger.info("label: " + item['label'])
            self.logger.info("size: " + "{:,}".format(item['size']))

    def getTorrent(self, hash):
        return self.myTorrents[hash]

    def getTorrentByPattern(self):
        """Return the hash of the smallest or largest torrent in the list."""
        myHash = ""
        myComparitor = 0
        pattern = self.pattern.lower()
        if 'newest' in pattern:
            for hash, item in self.myTorrents.items():
                if myComparitor > item['created'] or myHash == "":
                    myComparitor = item['created']
                    myHash = hash
            return myHash
        elif 'oldest' in pattern:
            for hash, item in self.myTorrents.items():
                self.logger.debug(item['size'])
                if myComparitor < item['created'] or myHash == "":
                    self.logger.debug(item['name'])
                    myComparitor = item['size']
                    myHash = hash
            return myHash
        elif 'smallest' in pattern:
            for hash, item in self.myTorrents.items():
                self.logger.debug(item['size'])
                if myComparitor > item['size'] or myHash == "":
                    self.logger.debug(item['name'])
                    myComparitor = item['size']
                    myHash = hash
            return myHash
        elif 'largest' in pattern:
            for hash, item in self.myTorrents.items():
                self.logger.debug(item['size'])
                if myComparitor < item['size'] or myHash == "":
                    self.logger.debug(item['name'])
                    myComparitor = item['size']
                    myHash = hash
            return myHash
        else:
            self.logger.error("Unhandled search pattern.  Must be newest, oldest, smallest, or largest.")
            return False  #Something went wrong

    def getFileWithSCP(self, file, recursive, label):
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.server, username=self.username, password=self.password)
        # Where are we putting this?  Make the folder if it doesn't already exist

        downloadLocation = self.localSavePath + label + "/"
        if not os.path.exists(downloadLocation):
            try:
                os.makedirs(downloadLocation)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        # SCPCLient takes a paramiko transport as an argument
        scp = SCPClient(ssh.get_transport())
        # try:
        scp.get(file, downloadLocation, recursive=recursive)
        return True

    def downloadAndLabelByHash(self, hash):
        self.setLabel(hash,'downloading')
        if self.checkIfAlreadyDownloaded(hash):
            if 'skip' in self.duplicate_action:
                self.setLabel(hash,'duplicate')
                self.logger.warn("Skipping because of duplicate action preference")
                del self.myTorrents[hash]
                return False
            elif 'overwrite' in self.duplicate_action:
                self.logger.warn("Overwriting because of duplicate action preference")
                self.deleteLocalDownload(hash)
                if self.getFileWithSCP(self.myTorrents[hash]['file_path'], self.myTorrents[hash]['multi_file'],self.myTorrents[hash]['label']):
                    self.setLabel(hash,'downloaded')
                    del self.myTorrents[hash]
                    return True
        else:
            if self.getFileWithSCP(self.myTorrents[hash]['file_path'], self.myTorrents[hash]['multi_file'],self.myTorrents[hash]['label']):
                self.setLabel(hash,'downloaded')
                del self.myTorrents[hash]
                return True

    def deleteLocalDownload(self, hash):
        downloadLocation = self.localSavePath + self.myTorrents[hash]['label'] + "/" + self.myTorrents[hash]['file_path'].rsplit('/', 1)[-1]
        if self.myTorrents[hash]['multi_file']:
            try:
                shutil.rmtree(downloadLocation)
            except OSError, e:
                print ("Error: %s - %s." % (e.filename, e.strerror))
        else:
            if os.path.isfile(downloadLocation):
                os.remove(downloadLocation)
            else:    ## Show an error ##
                print("Error: %s file not found" % downloadLocation)


    def checkIfAlreadyDownloaded(self, hash):
        downloadLocation = self.localSavePath + self.myTorrents[hash]['label'] + "/" + self.myTorrents[hash]['file_path'].rsplit('/', 1)[-1]
        self.logger.info(downloadLocation)
        if os.path.exists(downloadLocation):
            self.logger.info("Uh oh, "+ self.myTorrents[hash]['label'] + "already exists!")
            # if os.path.getsize(downloadLocation) < self.myTorrents[hash]['size']):
            #     self.logger.info("Downloaded size is less than what's on server so ")
            # else:
            #     self.logger.info("Downloaded size equals size on server")
            #     return true
            self.logger.info("Local size: " + str(os.path.getsize(downloadLocation)))
            self.logger.info("Server size: " + str(self.myTorrents[hash]['size']))
            return True
        else:
            return False

    def setLabel(self, hash, label):
        url = "http://" + self.server + self.ruTorrentPath + "/httprpc/action.php"
        payload = {'mode': 'setlabel', 'hash': hash, 's': 'label', 'v':	label }
        headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
        response = requests.request("POST", url, data=payload, headers=headers, auth=(self.username,self.password))
        json_data = response.json()

    def downloadTorrentsByPattern(self):
        self.grabTorrents()
        didDownloadsHappen = False
        while self.myTorrents:
            nextTorrent = self.getTorrentByPattern()
            self.logger.info("Download Queue Size: " + str(len(self.myTorrents)))
            self.logger.info("Downloading " + self.myTorrents[nextTorrent]['name'] + "  size: " + "{:,}".format(self.myTorrents[nextTorrent]['size']))
            downloadSize = self.myTorrents[nextTorrent]['size']
            preDownloadTime = time.time()
            self.downloadAndLabelByHash(nextTorrent)
            didDownloadsHappen = True
            postDownloadTime = time.time()
            downloadTime = postDownloadTime - preDownloadTime
            self.logger.info("Download took " + str(downloadTime) + " seconds")
            self.logger.info("Download Speed: " +  "{:,}".format(round((downloadSize/downloadTime)/1024)) + " kilobytes/second")
            self.logger.info("Delay for 5 seconds to give labels a chance to be applied.")
            time.sleep(5)
            self.grabTorrents()
        self.logger.debug("Finished with all Downloads!")
        return didDownloadsHappen
