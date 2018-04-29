#!/usr/bin/python3

import re
import subprocess
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def GetfilerList(filerList, filePath = '/etc/hosts'):
    try:
        f = open(filePath, 'r')
    except:
        print(filePath, ': no such file or directory')
        return False
    else:
        for i in f:
            if not (re.match('^#', i) or re.search('offline', i)) and re.search('.*TW.*NAS\s*$', i):
                filerList.append(re.split('\s+', i)[1])
    f.close()

def IsAlive(filerName):
    cmd = '/bin/ping -c1 -W1 {filerName}'
    p = subprocess.Popen(cmd.format(filerName = filerName),
            stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
    out, err = p.communicate()
    if p.returncode == 0:
        return True
    else:
        return False

def GetVolumeList(filerName, intactList):
    cmd = '/usr/bin/rsh {0} vol status'
    p = subprocess.Popen(cmd.format(filerName), stdout = subprocess.PIPE, stderr = subprocess.PIPE,
            shell = True)
    out, err = p.communicate()
    intactList[filerName] = re.findall(r'(\w+) online', str(out))

def CheckAutoDelete(filerName, intactList):
    cmd = '/usr/bin/rsh {filerName} snap autodelete {volumeName} show'
    for i in list(intactList[filerName]):
        p = subprocess.Popen(cmd.format(filerName = filerName, volumeName = i),
                stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
        out, err = p.communicate()
        if re.search('state.*: off', str(out)):
            intactList[filerName].remove(i)

def IsMatching(filerName, volumeName, msgLine):
    if re.search('Deleting\ssnapshot.*' + volumeName, msgLine):
        return True
    else:
        return False

def FilterMessage(msgLine, filerName, volumeName):
    tmp = re.findall("snapshot '(.*)' in", msgLine)
    s = '{filerName:10} | {volumeName:15} | {time:20} | {snapshot:46} |\n'
    return s.format(filerName = filerName, volumeName = volumeName, time = msgLine[0:19], snapshot = tmp[0])

def SendMail(message):
    fromaddr = 'ms03@example.com'
    toaddr = ['andrew@example.com']
    toaddr.append('tom@example.com')
    header = MIMEMultipart()
    header['from'] = fromaddr
    header['to'] = ', '.join(toaddr)
    header['subject'] = 'Snapshot of NAS weekly report'
    header.attach(MIMEText(message))
    s = smtplib.SMTP('192.168.2.100')
    s.sendmail(header['from'], toaddr, header.as_string())
    s.quit()

if __name__ == '__main__':
    intactList = {}
    filerList = []
    title = '{filerName:10} | {volumeName:15} | {time:20} | {snapshot:46} |\n'
    message = title.format(filerName = 'Filer name', volumeName = 'Volume name',
            time = 'Deletion time', snapshot = 'Snapshot name')
    message += ('-' * 101 + '|\n')

    GetfilerList(filerList)
    for i in filerList:
        if IsAlive(i):
            GetVolumeList(i, intactList)
            CheckAutoDelete(i, intactList)
            for v in intactList[i]:
                try:
                    msgpath = '/net/' + i + '/vol/vol0/etc/messages.0'
                    f = open(msgpath, 'r')
                except IOError:
                    print(msgpath, ': no such file or directory')
                    break
                else:
                    for l in f:
                        if IsMatching(i, v, l):
                            message += FilterMessage(l, i, v)
                    f.close()
    SendMail(message)
