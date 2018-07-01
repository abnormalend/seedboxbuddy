# SeedBoxBuddy
(readme a work in progress)

## Quick Start
- Copy the sample config to settings.ini, and add your seedbox credentials.
- Run sbb.py

## What it does
Automatically download from your seedbox on the schedule you define, and label torrents once they've been downloaded.

## Features
### Download Schedule
Set a start and stop time to control when your downloads happen, like in the middle of the night.
### Control Downloads by Label
Define a list of labels to ignore, label torrents that are in the middle of downloading, and then mark torrents that have been finished downloading so you know they can be deleted when you are finished seeding.
### Choose your download order
Supports 4 different orders of downloading:
- smallest
- largest
- oldest
- newest

## Notes
- Requires ruTorrent


## Docker Notes
### Time Zone
Container will run in UTC time zone unless specified.  Supports setting the time zone by environment variable TZ.  

**Example:**
> TZ=America/Detroit


[List of time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

### Folders
When running inside docker, it will look for the settings.ini inside of /config rather than the program directory.  The default download folder is /download.  Map volumes to both these points to store your settings and send your downloads to your intended storage location.

### Example Docker Start
```bash
docker create \
    --name seedboxybuddy \
    -e TZ=US/Detroit \
    -v $configDir:/config \
    -v $downloadDir:/download \
    abnormalend/seedboxbuddy
```
