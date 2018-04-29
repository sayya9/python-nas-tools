#!/usr/bin/python3

import re
import os
import sys
import subprocess
import smtplib
import socket
from optparse import OptionParser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def IsRoot():
    if os.getuid() == 0:
        return True
    else:
        return False

def IsMgr(hostname):
    if hostname == 'ms02' or hostname == 'ms03':
        return True
    else:
        return False

def GetFilerList(filerList, filePath = '/etc/hosts'):
    try:
        f = open('/etc/hosts')
    except:
        print(filePath, ': no such file or directory')
        return False
    else:
        for i in f:
            if not re.search('^#|offline', i) and re.search('.*(TW|US).*NAS\s*$', i):
                filerList.append(re.split('\s+', i)[1])
    f.close()

def IsAlive(filerName):
    cmd = 'ping -c1 -W1 ' + filerName
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        return True
    else:
        return False

def GetVolumeList(filerName):
    cmd = '/usr/bin/rsh ' + filerName + ' vol status'
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    t = re.findall('(\w+\s+online.*)', out.decode())
    volumeList = []
    for i in t:
        if not re.search('snapmirror|vol0', i):
            volumeList.append(re.split(' ', i)[0])
    return volumeList

def VerifyQuota(filer, volumeList):
    cmd = ['/usr/bin/rsh', filer, 'quota', 'report']
    output = subprocess.check_output(cmd)
    content = ''
    for i in volumeList:
        for j in 'user', 'group', 'tree':
            x = re.compile(j + '\s+\*\s+' + i)
            content += (filer + ' ' + i + ' ' + j + '\n') if not x.search(output.decode()) else ''
    return content

def SendMail(hostname, content):
    fromaddr = hostname + '@example.com'
    toaddr = ['andrew@example.com']
    header = MIMEMultipart()
    header['from'] = fromaddr
    header['to'] = ', '.join(toaddr)
    header['subject'] = 'Unconfigurable filer quotas information'
    header.attach(MIMEText(content))
    s = smtplib.SMTP('192.168.2.100')
    s.sendmail(header['from'], toaddr, header.as_string())
    s.quit()

if __name__ == '__main__':
    usage = 'Usage: %prog [-c] [-h]'
    parser = OptionParser(usage = usage)
    parser.add_option('-c', '--check', action = 'store_true',
            help = 'check all filers for quota and export enabling')
    (options, args) = parser.parse_args()
    hostname = socket.gethostname()
    if len(args) != 0:
        parser.error('wrong number of arguments')
        sys.exit(1)
    elif not IsRoot():
        print('you must run the command as superuser privileges')
        sys.exit(1)
    elif not IsMgr(hostname):
        print('you must run the command on the management server ms02')
        sys.exit(1)
    elif options.check:
        filerList = []
        GetFilerList(filerList)
        content = ''
        for i in filerList:
            if not IsAlive(i):
                print(i + ' is not alive')
                filerList.remove(i)
            else:
                volumeList = GetVolumeList(i)
                content += VerifyQuota(i, volumeList) if len(volumeList) != 0 else ''
        if content:
            SendMail(hostname, content)

    else:
        parser.print_help()
        sys.exit(1)
