#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=import-error
"""
(c) 2020 Jiri Zahradil, jz@zahradil.info

Aplication for managing backups and snapshots created via hard-links.

Definitions:
------------

ORIGIN - data volume
    place(directory) of your files you want to backup

BACKUP - backup volume
    /mirror
       - special directory on backup volume that is used
         to mirror BACKUP volume

         in case that ORIGIN and BACKUP volume are stored
         on the same volume, MIRROR will not be used.
         In other cases we use rsync for maintaining MIRROR
         in sync with BACKUP.

    Same/different volume is checked by:
    df -P "%s" | awk 'END{print $1}'

    /snapshot-XXX
        stored hard-linked snapshots
        # cp -al $MIRROR $BACKUP/snapshot-$(date '+%Y%m%d%H%M')

Configuration:
--------------
    It used to store defaults for calling one backup task.
    It is stored in python .conf file:

    [backuptask1]
    logfile=/var/log/jzh-backup.log
    # logfile=syslog
    # logfile=none
    loglevel=INFO

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

    rsync-options=""


Instalation:
------------
- it needs python3 and python3-venv (virtualenv) packages

> download file jzhb-1.0-bin.tgz
> tar xf jzhb-1.0-bin.tgz
> cd jzhb-1.0
> ./install.sh

then:
    1) jzhbck "user" util is installed to ~/bin/
    2) you can use <installation-dir>/jzhb to call it in locally
    3) you should copy default.conf to your own configuration file
       and modify it according to your backup locations
       configuration file is param to calling jzhbck


Example:
--------

> jzhbck backup my.conf backuptask1

"""

import click, configparser
import subprocess
import os, sys, os.path, re, datetime as dt, shutil

NICE_PREFIX="nice ionice -c3 "

class CriException(RuntimeError):
    pass

def filtersnaps(snaps, ops):
    for i in ops:
        if i in snaps:
            del snaps[i]
    return snaps

def parsedatestring(s):
    year = int(s[0:4])
    mo = int(s[4:6])
    d = int(s[6:8])
    h = int(s[8:10])
    mn = int(s[10:12])
    return dt.datetime(year, mo, d, h, mn, 0, 0)

def unlinkdir(dir):
    try:
        shutil.rmtree(dir, ignore_errors=True)
    except Exception as e:
        click.echo("Exception during delete %s" % (str(e)))

def renamedir(fn1, fn2):
    try:
        os.rename(fn1, fn2)
    except Exception as e:
        click.echo("Exception during rename %s" % (str(e)))

def carry_all_ops(backup_path, ops):
    # click.echo("carry_all_ops")
    pocet = 0
    for fn1, fn2 in ops.items():
        if not fn2:
            click.echo("Unlink: %s" % (fn1))
            unlinkdir(os.path.join(backup_path, fn1))
            pocet += 1
            continue
        if fn1==fn2:
            # print("NOP %s" % (fn1))
            continue
        click.echo("Rename %s -> %s" % (fn1, fn2))
        renamedir(os.path.join(backup_path, fn1), os.path.join(backup_path, fn2))
        pocet += 1
        continue
    click.echo("Total %d ops" % (pocet))
    return None

def clearing(backup_path, cfg, section):
    PREFIX = "snapshot-"

    LEAVE1_DAYS  = cfg.getint(section, "untouch-days", fallback=7)
    LEAVE2_DAYS  = LEAVE1_DAYS+cfg.getint(section, "oneper-day", fallback=30)
    LEAVE3_WEEK  = cfg.getint(section, "oneper-weeks", fallback=4)
    LEAVE3_DAYS  = LEAVE2_DAYS+LEAVE3_WEEK*7
    LEAVE4_DAYS  = LEAVE3_DAYS+cfg.getint(section, "oneper-month", fallback=12)*31 # x měsíců

    DELETE_BAD_SNAPS = cfg.getboolean(section, "delete-unknown-snapshots", fallback=False)

    snaps = dict()
    nyni = dt.datetime.now()
    ops = dict()

    for fn in os.listdir(backup_path):
        if fn == "mirror":
            continue
        if not fn.startswith(PREFIX):
            # print("skipped:%s" % (fn))
            if DELETE_BAD_SNAPS:
                ops[fn] = None
            continue
        d = fn[len(PREFIX):]
        snaps[fn] = d

    # click.echo("All snaps count: %d" % (len(snaps)))
    all_snaps_len = len(snaps)
    if DELETE_BAD_SNAPS:
        click.echo("Erasing bad snaps along the way.")

    # 0) bad ones
    for fn, d in snaps.items():
        if len(d) != 12:
            click.echo("bad: %s"%(fn))
            if DELETE_BAD_SNAPS:
                ops[fn] = None
            else:
                ops[fn] = fn
            continue

        if not d.startswith("20"):
            click.echo("bad prefix: %s" % (fn))
            if DELETE_BAD_SNAPS:
                ops[fn] = None
            else:
                ops[fn] = fn
            continue
        continue

    filtersnaps(snaps, ops)
    if len(snaps) != all_snaps_len:
        click.echo("All good snaps count=%d" % (len(snaps)))

    # 1) last 7 days
    d7 = nyni - dt.timedelta(days=LEAVE1_DAYS)
    d7 = d7.replace(hour=0, minute=0)
    ds = d7.strftime("%Y%m%d")
    for fn, d in sorted(snaps.items(), key=lambda x: x[1]):
        if d>ds:
            ops[fn] = fn

    filtersnaps(snaps, ops)

    # 2) leave 1 per day
    d30 = nyni - dt.timedelta(days=LEAVE2_DAYS)
    d30 = d30.replace(hour=0, minute=0)
    ds = d30.strftime("%Y%m%d")
    days = set()
    for fn, d in sorted(snaps.items(), key=lambda x: x[1]):
        if d<ds:
            continue
        den = d[:6]
        if den in days:
            ops[fn] = None
            continue

        days.add(den)
        ops[fn] = fn
        continue

    filtersnaps(snaps, ops)

    # 3) leave 1 per week
    d4w = nyni - dt.timedelta(days=LEAVE3_DAYS)
    d4w = d4w.replace(hour=0, minute=0)
    ds = d4w.strftime("%Y%m%d")
    weeks = set()
    for fn, d in sorted(snaps.items(), key=lambda x: x[1]):
        if d<ds:
            continue
        d1 = parsedatestring(d)
        _isoyear, weeknum, _dow = d1.isocalendar()
        if weeknum in weeks:
            ops[fn] = None
            continue

        weeks.add(weeknum)
        ops[fn] = fn
        continue

    filtersnaps(snaps, ops)

    # 4) leave 1 per month
    d12m = nyni - dt.timedelta(days=LEAVE4_DAYS)
    d12m = d12m.replace(hour=0, minute=0)
    ds = d12m.strftime("%Y%m%d")
    months = set()
    for fn, d in sorted(snaps.items(), key=lambda x: x[1]):
        if d<ds:
            continue
        mn = d[4:6]
        if mn in months:
            ops[fn] = None
            continue

        months.add(mn)
        ops[fn] = fn
        continue

    filtersnaps(snaps, ops)

    # handle REST
    for fn, d in sorted(snaps.items(), key=lambda x: x[1]):
        click.echo("Reziduum: %s" % (fn))

    # print("Operations (including NOP) counts=%d" % (len(ops)))
    # print(repr(ops))
    carry_all_ops(backup_path, ops)


def load_config(cfgfile):
    cfg = configparser.SafeConfigParser()
    cfg.read(cfgfile)
    return cfg

def check_backup_structure(pth):
    if not os.path.exists(pth):
        click.echo()
        raise CriException("Path %s does not exists." % (pth))
    m1 = os.path.join(pth, "mirror")
    if not os.path.exists(m1):
        os.mkdir(m1)
    return

def exec_and_get_stdout(cmd):
    p = subprocess.Popen(cmd, shell=True,
            stdin=None, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    (_, w) = (p.stdin, p.stdout)
    result = "".join(i.decode("utf-8") for i in w.readlines())
    result = result.strip()
    w.close()
    return result

def exec_and_get_lines(cmd):
    p = subprocess.Popen(cmd, shell=True,
            stdin=None, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    (_, w) = (p.stdin, p.stdout)
    result = [i.decode("utf-8").strip() for i in w.readlines()]
    w.close()
    return result


def try_unlink(filename):
    try:
        os.unlink(filename)
    except:
        pass

def is_same_filesystem(pth1, pth2):
    tpl = "df -P \"%s\" | awk 'END{print $1}'"
    fs1 = exec_and_get_stdout(tpl % (pth1))
    fs2 = exec_and_get_stdout(tpl % (pth2))
    if fs1 and fs2:
        if fs1==fs2:
            click.echo("filesystems matched")
            return True
        else:
            click.echo("Filesystems differs[%s/%s]" % (fs1,fs2))
            return False

    click.echo("Filesystems unsure[%s/%s]" % (fs1,fs2))
    return False

def snapshot_with_cp(src, dst, nice=False):
    click.echo("snapsthot_with_cp")
    cmdr = "cp -al \"%s\" \"%s\"/snapshot-$(date '+%%Y%%m%%d%%H%%M')" % (src, dst)
    if nice:
        cmdr = NICE_PREFIX + cmdr
    res = exec_and_get_stdout(cmdr)
    click.echo(res)
    return

def backup_with_rsync(src, dst, nice=False):
    click.echo("backup_with_rsync")
    opts1=""
    opts2="--no-o --no-g --no-p --delete"
    cmdr ="rsync -ax -u -v %s %s \"%s/\" \"%s/\"" % (opts1, opts2, src, dst)
    if nice:
        cmdr = NICE_PREFIX + cmdr
    res = exec_and_get_stdout(cmdr)
    click.echo(res)
    return



@click.group()
def cli():
    """Aplication for managing backups and snapshots created via hard-links.

App manages efficiently directory structure of hard-link created
backups of original data location. You can make backups every few hours,
but app will ensure that older backups are pruned, so you will still have
manageable amount of backups.

\b
Policy: - last 7 days - leave all untouched
 then: - leave 1 per day for 30 days
 then: - leave 1 per week for 4 weeks
 then: - leave 1 per month for 12 months

"""
    pass

@cli.command()
@click.argument('cfgfile')
@click.argument('location')
@click.option("--force", is_flag=True, help="Force backup even if it is too early.")
def backup(location, cfgfile, force):
    """Do one snapshot if last snapshot is older than min-age-hours."""
    cfg = load_config(cfgfile)
    section = location
    if force:
        click.echo("Yay, forced!")
    else:
        click.echo("Hey!")

    b_nice = cfg.getboolean(section, "be-nice", fallback=False)
    ORIGIN = cfg.get(section, "origin")
    BACKUP = cfg.get(section, "backup")
    MIRROR = os.path.join(BACKUP, "mirror")
    click.echo("ORIGIN: "+ORIGIN)
    click.echo("BACKUP: "+BACKUP)

    check_backup_structure(BACKUP)

    if is_same_filesystem(ORIGIN, MIRROR):
        # zalohuj přes cp
        snapshot_with_cp(ORIGIN, BACKUP, nice=b_nice)
    else:
        # nejdřív rsync
        backup_with_rsync(ORIGIN, MIRROR, nice=b_nice)
        snapshot_with_cp(MIRROR, BACKUP, nice=b_nice)

    clearing(BACKUP, cfg, section)

@cli.command()
@click.argument('cfgfile')
@click.argument('location')
def status(location, cfgfile):
    """Print summary statistical information, disk usage, etc."""
    cfg = load_config(cfgfile)
    section = location
    ORIGIN = cfg.get(section, "origin")
    BACKUP = cfg.get(section, "backup")
    MIRROR = os.path.join(BACKUP, "mirror")

    if is_same_filesystem(ORIGIN, MIRROR):
        res = exec_and_get_lines("du \"%s\"/* \"%s\" -shc" % (BACKUP, ORIGIN))
    else:
        res = exec_and_get_lines("du \"%s\"/* -shc" % (BACKUP))

    for line in res:
        if line.endswith("total"):
            click.echo(line)

@cli.command('list')
@click.argument('cfgfile')
@click.argument('location')
def listcommand(location, cfgfile):
    """List all snapshots with their usage information"""
    cfg = load_config(cfgfile)
    section = location
    BACKUP = cfg.get(section, "backup")

    res = exec_and_get_lines("du \"%s\"/* -shc" % (BACKUP))

    for line in res:
        click.echo(line)

@cli.command('clearing')
@click.argument('cfgfile')
@click.argument('location')
def only_clearing(location, cfgfile):
    """Just clear obsolete snapshots."""
    cfg = load_config(cfgfile)
    section = location
    BACKUP = cfg.get(section, "backup")
    clearing(BACKUP, cfg, section)

@cli.command()
def restore():
    """This will restore data from snapshot or mirror to new destination
        or you can specify --origin to overwrite original destination $ORIGIN
        if possible, it is recommended because of safety to do "force-backup"
        first, before running "restore" to $ORIGIN."""
    click.echo("restore not implemented")

if __name__ == '__main__':
    try:
        cli()
    except CriException as exc:
        click.echo(exc)
        click.echo("Finished.")
