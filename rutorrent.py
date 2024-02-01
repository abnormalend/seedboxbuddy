#!/home/brent/seedboxbuddy/venv/bin/python3
"""Manges a connection to ruTorrent."""
import logging
import requests
import time
import os
import json
import shutil
import paramiko
import boto3
import botocore
import errno
from paramiko import SSHClient
from scp import SCPClient

class RuTorrent:
    """Functions and things for managing an rutorrent server."""
    __version__ = "1.0.2"

    def __init__(self, config, logger):

        # self.logger = logging.getLogger("sbb."+__name__)
        self.logger = logger

        self.myTorrents = {}
        self.server =config['settings']['myServer']
        self.ruTorrentPath = config['settings']['myTorrentPath']
        self.myTorrentFilePath = config['settings']['myTorrentFilePath']
        self.username = config['settings']['myUsername']
        self.password = config['settings']['myPassword']
        self.ignoreLabels = config['settings']['ignoreLabels'].split(',')
        self.maxSize = self.parse_size(config['settings']['maxSize'])
        self.logger.info(self.maxSize)
        self.pattern = config['settings']['downloadPattern']
        self.localSavePath = config['settings']['localSavePath']
        self.duplicate_action = config['settings']['duplicate_action'].lower()
        self.grabtorrent_retry_count = int(config['settings']['grabtorrent_retry_count'])
        self.grabtorrent_retry_delay = int(config['settings']['grabtorrent_retry_delay'])
        self.s3_enabled = config['settings'].getboolean('s3_enabled')
        self.s3_bucket = config['settings']['s3_bucket']
        self.s3_aws_cli_loc = config['settings']['s3_aws_cli_loc']
        self.s3_key = config['settings']['s3_key']
        self.s3_secret = config['settings']['s3_secret']
        # self.autolabel = dict(config['autolabel'])
        # self.grabTorrents()
        self.ssh = None

    # Parse the filesize
    def parse_size(self, size):
        """Translates the size from string with units to integer."""
        units = {"B": 1, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
        self.logger.debug(size)
        if len(size.split()) > 1:
            number, unit = [string.strip() for string in size.split()]
            return int(float(number)*units[unit])
        else:
            return int(size)

    def getVersion(self):
        return self.__version__

    def initSSH(self):
        self.ssh = SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.server, username=self.username, password=self.password)

    def takedownSSH(self):
        self.ssh.close()

    def grabTorrents(self):
        url = "http://" + self.server + self.ruTorrentPath + "/httprpc/action.php"
        payload = {'mode': 'list'}
        headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
        json_data = None
        for attempt in range(self.grabtorrent_retry_count):
            try:
                self.logger.debug("Try #" + str(attempt))
                response = requests.request("POST", url, data=payload, headers=headers, auth=(self.username,self.password))
                json_data = response.json()
            except Exception as e:
                self.logger.error("something has gone wrong, unable to download torrent lists.  Will retry in " + str(self.grabtorrent_retry_delay) + " seconds.")
                # self.logger.error(e)
                time.sleep(self.grabtorrent_retry_delay)
            else:
                break
        i = 0
        if json_data:
            for item in list(json_data["t"].items()):
                if item[1][14] not in self.ignoreLabels and int(item[1][5]) < self.maxSize and int(item[1][19]) == 0:
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
            self.logger.info("Torrents loaded successfully from ruTorrent. " + str(len(self.myTorrents)) + " records loaded.")
            return True
        else:
            self.logger.error("unable to download")
            return False

    def getAllTorrents(self):
        self.logger.info("Printing all torrent details")
        print(self.myTorrents)
        for hash, item in list(self.myTorrents.items()):
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
            for hash, item in list(self.myTorrents.items()):
                if myComparitor > item['created'] or myHash == "":
                    myComparitor = item['created']
                    myHash = hash
            return myHash
        elif 'oldest' in pattern:
            for hash, item in list(self.myTorrents.items()):
                self.logger.debug(item['size'])
                if myComparitor < item['created'] or myHash == "":
                    self.logger.debug(item['name'])
                    myComparitor = item['size']
                    myHash = hash
            return myHash
        elif 'smallest' in pattern:
            for hash, item in list(self.myTorrents.items()):
                self.logger.debug(item['size'])
                if myComparitor > item['size'] or myHash == "":
                    self.logger.debug(item['name'])
                    myComparitor = item['size']
                    myHash = hash
            return myHash
        elif 'largest' in pattern:
            for hash, item in list(self.myTorrents.items()):
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
        # ssh = SSHClient()
        # ssh.load_system_host_keys()
        # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh.connect(self.server, username=self.username, password=self.password)
        # Where are we putting this?  Make the folder if it doesn't already exist

        downloadLocation = self.localSavePath + label + "/"
        if not os.path.exists(downloadLocation):
            try:
                os.makedirs(downloadLocation)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        # SCPCLient takes a paramiko transport as an argument
        scp_client  = SCPClient(self.ssh.get_transport())
        try:
            scp_client.get(file, downloadLocation, recursive=recursive)
            return True
        except paramiko.SCPException as e:
            self.logger.error("download error: " + str(e))
            return False

    def getFileWithS3(self, file, recursive, label):
        stdin = None
        stdout = None
        stderr = None
        try:
            if not recursive:
                stdin, stdout, stderr = self.ssh.exec_command(self.s3_aws_cli_loc + ' s3 cp "' + file + '" s3://' + self.s3_bucket + "/" + label + "/")
            else:
                stdin, stdout, stderr = self.ssh.exec_command(self.s3_aws_cli_loc + ' s3 cp --recursive "' + 
                                                                file + '/" s3://' + self.s3_bucket + '/"' + label + '"/"' + 
                                                                file.replace(self.myTorrentFilePath, '') + '"/')
            if stdout:
                self.logger.debug("STDOUT:")
                for line in stdout.readlines():
                    self.logger.debug(line)
            if stderr:
                self.logger.debug("STDERR:")
                for line in stderr.readlines():
                    self.logger.debug(line)
            return True
        except paramiko.SSHException as e:
            self.logger.error(e)
            self.logger.error("stdin: " + stdin.readlines())
            self.logger.error("stdout: " + stdout.readlines())
            self.logger.error("stderr: " + stderr.readlines())
            return False


    def createPathLocally(self, path):
        """S3 download will not create subdirectories, so we need to ensure they are created."""
        os.makedirs(os.path.dirname(path), mode = 0o777, exist_ok = True)

    def getFromS3toLocal(self):
        s3 = boto3.resource('s3',
                        aws_access_key_id=self.s3_key,
                        aws_secret_access_key=self.s3_secret)
        bucket = s3.Bucket(self.s3_bucket)
        bucket_files = [x.key for x in bucket.objects.all()]
        for s3_file in bucket_files:
            self.logger.debug("Downloading from S3: " + s3_file)
            local_path = self.localSavePath + s3_file
            self.createPathLocally(local_path)
            bucket.download_file(s3_file, local_path)


    def deleteS3files(self):
        """This will delete all files in the S3 bucket, so don't run this on just any bucket."""
        s3 = boto3.resource('s3',
                        aws_access_key_id=self.s3_key,
                        aws_secret_access_key=self.s3_secret)
        bucket = s3.Bucket(self.s3_bucket)
        bucket_files = [x.key for x in bucket.objects.all()]
        delete_objects = []
        if bucket_files:
            for s3_file in bucket_files:
                delete_objects.append({'Key': s3_file})
            try:
                response = bucket.delete_objects(Delete={ 'Objects': delete_objects}    )
            except botocore.exceptions.ClientError as e:
                self.logger.error(e)
                self.logger.error(delete_objects)
                return False

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
            if self.s3_enabled:
                if self.getFileWithS3(self.myTorrents[hash]['file_path'], self.myTorrents[hash]['multi_file'],self.myTorrents[hash]['label']):
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
            except OSError as e:
                print(("Error: %s - %s." % (e.filename, e.strerror)))
        else:
            if os.path.isfile(downloadLocation):
                os.remove(downloadLocation)
            else:    ## Show an error ##
                print(("Error: %s file not found" % downloadLocation))


    def checkIfAlreadyDownloaded(self, hash):
        downloadLocation = self.localSavePath + self.myTorrents[hash]['label'] + "/" + self.myTorrents[hash]['file_path'].rsplit('/', 1)[-1]
        self.logger.debug(downloadLocation)
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
        if self.myTorrents:
            self.initSSH()
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
                self.logger.info("Download took " + str(round(downloadTime)) + " seconds")
                if (downloadSize/downloadTime)/1024 > 1000:
                    self.logger.info("Download Speed: " +  "{:,}".format(round((downloadSize/downloadTime)/1024/1024)) + " megabytes/second")
                else:
                    self.logger.info("Download Speed: " +  "{:,}".format(round((downloadSize/downloadTime)/1024)) + " kilobytes/second")
                self.logger.info("Delay for 5 seconds to give labels a chance to be applied.")
                time.sleep(5)
                self.grabTorrents()
            self.takedownSSH()
            if self.s3_enabled:
                self.logger.info("All files transferred to S3, now copying to local storage.")
                self.getFromS3toLocal()
                self.deleteS3files()
            self.logger.info("Finished with all Downloads!")
        return didDownloadsHappen

    def get_deletable_torrents(self):
        url = "http://" + self.server + self.ruTorrentPath + "/httprpc/action.php"
        payload = {'mode': 'list'}
        headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache",}
        json_data = None
        for attempt in range(self.grabtorrent_retry_count):
            try:
                self.logger.debug("Try #" + str(attempt))
                response = requests.request("POST", url, data=payload, headers=headers, auth=(self.username,self.password))
                json_data = response.json()
            except Exception as e:
                self.logger.error("something has gone wrong, unable to download torrent lists.  Will retry in " + str(self.grabtorrent_retry_delay) + " seconds.")
                # self.logger.error(e)
                time.sleep(self.grabtorrent_retry_delay)
            else:
                break
        i = 0
        if json_data:
            for item in list(json_data["t"].items()):
                # Must be downloaded, ratio > 1 (item 10), and finished (item 3)
                if item[1][14] == 'downloaded' and int(item[1][3]) == 0:
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
            self.logger.info("Torrents loaded successfully from ruTorrent. " + str(len(self.myTorrents)) + " records loaded.")
            return True
        else:
            self.logger.error("unable to download")
            return False
    
    def recursiveDeleter(self, sftp, path):
        """Get the list of files, try to delete.  If we get an OS error, recursively enter that path"""
        try:
            file_list = sftp.listdir(path=path)
        except FileNotFoundError:
            try:
                sftp.remove(path)
                return True
            except FileNotFoundError:
                return False
        for file in file_list:
            try:
                self.logger.info(f"Attempting to delete {path}/{file}")
                sftp.remove(f"{path}/{file}")
            except OSError:
                self.logger.info(f"Could not delete {path}/{file}, assuming it is a non-empty directory")
                self.recursiveDeleter(sftp, f"{path}/{file}")
        sftp.rmdir(path)
        return True

    def deleteTorrentsAndFiles(self):
        self.initSSH()
        sftp = self.ssh.open_sftp()
        base_path = './data'
        for hash, item in self.myTorrents.items():
            self.logger.debug(f"hash: {hash}")
            self.logger.debug(item)
            if self.recursiveDeleter(sftp, f"{base_path}/{item['name']}"):
                self.deleteTorrent(hash)
            else:
                self.logger.warning("Not deleting torrent, may already be gone")

    def deleteTorrent(self, hash):
        url = "http://" + self.server + self.ruTorrentPath + "/httprpc/action.php"
        payload = {'mode': 'remove', 'hash': hash }
        headers = {'Content-Type': "application/x-www-form-urlencoded",'Cache-Control': "no-cache"}
        response = requests.request("POST", url, data=payload, 
                                    headers=headers, auth=(self.username,self.password))
        if response.status_code == 200:
            return True
        else:
            self.logger.warning("Something may have gone wrong while trying to delete a torrent.")
            return False
