#!/usr/bin/python3

import subprocess
import calendar
import ntplib
import time
import re
from datetime import datetime

def IsAlive(filerName):
    cmd = '/bin/ping -c1 -W1 {0}'
    p = subprocess.Popen(cmd.format(filerName), shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        return True
    else:
        return False

def CheckServerIP(filerName, NTP):
    cmd = '/usr/bin/rsh {0} options timed.servers {1}'
    p = subprocess.Popen(cmd.format(filerName, ''), shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out0, err0 = p.communicate()
    if p.returncode == 0 and not re.search(NTP, out0.decode()):
        p = subprocess.Popen(cmd.format(filerName, NTP), shell = True,
                stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out1, err1 = p.communicate()
        print('setup NTP ' + NTP + ' => ' + filerName)

def GetFilerTime(filerName):
    cmd = '/usr/bin/rsh {filerName} date'
    p = subprocess.Popen(cmd.format(filerName = filerName), shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        monthList = {v: k for k, v in enumerate(calendar.month_abbr)}
        t = re.split('\s+', out.decode('utf-8'))
        date = t[5] + '-' + str(monthList[t[1]]) + '-' + t[2]
        time = t[3]
    return datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S").timestamp()

def GetServerTime(NTP):
    c = ntplib.NTPClient()
    response = c.request(NTP, version = 3)
    return response.tx_time

def IsOverOneMinute(filerEpoch, serverEpoch):
    if abs(filerEpoch - serverEpoch) > 60.0:
        return True
    else:
        return False

def AdjustFilerTime(filerName, serverEpoch, NTP):
    humanReadable = datetime.fromtimestamp(int(serverEpoch))
    dateTimeArg = '{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}.{5:02d}'.format(
            humanReadable.year, humanReadable.month, humanReadable.day,
            humanReadable.hour, humanReadable.minute, humanReadable.second)
    cmd = '/usr/bin/rsh {0} options timed.enable off && ' + \
            '/usr/bin/rsh {0} date {1} && ' + \
            '/usr/bin/rsh {0} options timed.enable on && ' + \
            '/usr/bin/rsh {0} options timed.servers {2}'
    p = subprocess.Popen(cmd.format(filerName, dateTimeArg, NTP), shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()

if __name__ == '__main__':
    filer7List = ['nas01', 'nas02', 'nas03', 'nas10']
    if filer7List:
        c = ntplib.NTPClient()
        try:
            NTP = '172.21.69.1'
            response = c.request(NTP, version = 3)
        except:
            NTP = '172.21.69.2'
            response = c.request(NTP, version = 3)
    for i in filer7List:
        if IsAlive(i):
            filerEpoch = GetFilerTime(i)
            serverEpoch = GetServerTime(NTP)
            CheckServerIP(i, NTP)
            if IsOverOneMinute(filerEpoch, serverEpoch):
                print('over 60 seconds => ' + i)
                AdjustFilerTime(i, serverEpoch, NTP)
