
jzh-backup
=====================================

Names: `jzhb`, `jzhbck`

Utility for managing backups and snapshots created via hard-links.

App manages efficiently directory structure of hard-link created
backups of original data location. You can make backups every few hours,
but app will ensure that older backups are pruned, so you will still have
manageable amount of backups.

#### Default policy: 
 - last 7 days - leave all untouched
 - then: leave 1 per day for 30 days
 - then: leave 1 per week for 4 weeks
 - then: leave 1 per month for 12 months
 
 
## Definitions:

- **ORIGIN** - data volume - place(directory) of your files you want to backup
- **BACKUP** - backup volume
- **$BACKUP/mirror** - special directory on backup volume that is used to mirror BACKUP volume.
- **$BACKUP/snapshot-XXX** - stored hard-linked snapshots, created by `cp -al $MIRROR $BACKUP/snapshot-$(date '+%Y%m%d%H%M')`

In case that ORIGIN and BACKUP volume are stored
on the same volume, MIRROR will not be used.
In other cases we use rsync for maintaining MIRROR
in sync with BACKUP. Same/different volume is checked by `df -P "%s" | awk 'END{print $1}'`

## Configuration:

It used to store defaults for calling one backup task. It is stored in python .conf file:

    [backuptask1]
    origin=/home/jiri
    backup=/var/backup/home-jiri
    min-age-hours=6
    permissions=False
    be-nice=True
    delete-unknown-snapshots=True
    untouch-days=7
    oneper-day=30
    oneper-weeks=4
    oneper-month=12
    
    
## Installation:

Prerequisities: `python3` and `python3-venv` (virtualenv) packages.
You can create distributable `*bin.tgz` archive by running script `./build-zip.sh` in development directory.

Installation procedure then consists of these steps:

    download file jzhb-1.0-bin.tgz
    tar xf jzhb-1.0-bin.tgz
    cd jzhb-1.0
    ./install.sh

then:

 1) `jzhbck` "user" util is installed to `~/bin/`
 2) you can use `<installation-dir>/jzhb` to call it in locally
 3) you should copy `default.conf` to your own configuration file and modify it according to your backup locations configuration file is param to calling `jzhbck`

## Commands:

Running without parameters will show help. Also you can run `./jzhb <command> --help` to show help for individual command.

    backup    Do one snapshot if last snapshot is older than min-age-hours.
    clearing  Just clear obsolete snapshots.
    list      List all snapshots with their usage information
    restore   This will restore data from snapshot or mirror to new...
    status    Print summary statistical information, disk usage, etc.

## Example:

    jzhbck backup my.conf backuptask1
