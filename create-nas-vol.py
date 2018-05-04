#!/usr/bin/python3

import re
import os
import sys
import subprocess
import shutil
import smtplib
import socket
from optparse import OptionParser
from datetime import datetime

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

def IdentifyDomain(filer, xrd):
    if re.match('tw', filer):
        return 'twrd'
    elif re.match('cn', filer) and xrd:
        return 'cnrd'
    elif re.match('us', filer):
        return 'usrd'
    else:
        print(filer + ': no such domain')
        sys.exit(1)

def UpdateConf(srcFile, dstFile, filer, volumeName, category, domain):
    shutil.copy(srcFile, dstFile)
    accessList = {'hwrd': 'rw=10.10.9.0/24:10.10.0.0/16:10.11.0.0/16,' + \
            'root=10.10.9.0/24:10.10.5.1:10.10.5.9:10.10.5.10:10.10.5.131:10.10.5.132:' + \
            '10.10.5.161:10.10.5.164:10.10.26.161:10.10.27.1:10.11.4.36',
            'rrd': 'rw=10.10.9.0/24:10.60.0.0/16:10.60.51.169,' + \
            'root=10.10.9.0/24:10.60.50.1:10.60.50.2:10.60.50.3:10.60.55.171:' + \
            '10.60.55.187:10.60.51.169',
            'xrd': 'rw=10.10.9.0/24:10.60.70.0/23:10.60.51.169,' + \
            'root=10.10.9.0/24:10.60.70.1:10.60.70.2:10.60.51.169'}
    f = open(srcFile, 'a')
    if category == 'exports':
        exports = '/vol/' + volumeName + ' -sec=sys,' + \
                accessList[domain] + 'nosuid\n'
        f.write(exports)
        cmd = '/usr/bin/rsh ' + filer + ' exportfs -rv'
    elif category == 'quotas':
        comment = '#' * 50 + '\n# ' + filer + ':/vol/' + volumeName + \
                '\n' + '#' * 50 + '\n'
        #uQuotas = '*\t\t\t\tuser@/vol/' + volumeName + '\t\t-\t-\t-\t-\t-\n'
        #gQuotas = '*\t\t\t\tgroup@/vol/' + volumeName + '\t\t-\t-\t-\t-\t-\n'
        #tree = '*\t\t\t\ttree@/vol/' + volumeName + '\t\t-\t-\t-\t-\t-\n'
        f.write(comment)
        p = '{:22} {:28} {:6} {:6} {:6} {:6} {:6}\n'
        for i in 'user', 'group', 'tree':
            f.write(p.format('*', i + '@/vol/' + volumeName, '-', '-', '-', '-', '-'))
        cmd = '/usr/bin/rsh ' + filer + ' quota on ' + volumeName
    f.close()
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    p.wait()

def CreateVolume(filer, aggr, volumeName, size):
    cmd = '/usr/bin/rsh ' + filer + ' vol create ' + \
            volumeName + ' ' + aggr + ' ' + size
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    p.wait()
    tmp = p.stdout.readline().decode()
    print(tmp)
    if not re.search('containing\saggregate', tmp) or p.returncode != 0:
        return False
    else:
        cmd = '/usr/bin/rsh ' + filer + ' snap reserve ' + volumeName + ' 0'
        p = subprocess.Popen(cmd, shell = True,
                stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        p.wait()
        return True

def GetFilerList(filerList, filePath = '/etc/hosts'):
    try:
        f = open('/etc/hosts')
    except:
        print(filePath, ': no such file or directory')
        return False
    else:
        for i in f:
            if not (re.match('^#', i) or re.search('offline', i)) and re.search('.*HWRD.*NAS\s*$', i):
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
    volumeList = re.findall('(\w+) online', out.decode())
    try:
        volumeList.remove('vol0')
    except:
        print('no volume name vol0 found in ' + filerName)
    return volumeList

def SendMail(hostname, content):
    fromaddr = hostname + '@example.com'
    toaddr = ['andrew@example.com']
    header = MIMEMultipart()
    header['from'] = fromaddr
    header['to'] = ', '.join(toaddr)
    header['subject'] = 'Unconfigurable filer quotas information'
    header.attach(MIMEText(content))
    s = smtplib.SMTP('10.10.5.131')
    s.sendmail(header['from'], toaddr, header.as_string())
    s.quit()

if __name__ == '__main__':
    usage = 'Usage: %prog [-f filer -A aggr -n vol-name] [-s size] [-x]'
    parser = OptionParser(usage = usage)
    parser.add_option('-f', '--filer', metavar = 'filer-name',
            help = 'specify which filer to create the volume')
    parser.add_option('-A', '--aggr', metavar = 'aggr-name',
            help = 'specify the aggr name')
    parser.add_option('-n', '--name', metavar = 'vol-name',
            help = 'specify the volume name')
    parser.add_option('-x', '--xrd', action = 'store_true',
            help = 'X domain mode')
    parser.add_option('-s', '--size', metavar = 'vol-size',
            default = '100g', help = 'specify the volume size, 100G is default')
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
    elif options.filer and options.aggr and options.name:
        domain = IdentifyDomain(options.filer, options.xrd)
        if not IsAlive(options.filer):
            print(options.filer + ' is not alive')
            sys.exit(1)
        srcDir = '/net/' + options.filer + '/vol/vol0/etc'
        dstDir = '/tmp/filer_conf'
        if not os.path.isdir(srcDir):
            print(srcDir + ': no such directory')
            sys.exit(1)
        elif not os.path.isdir(dstDir):
            os.mkdir(dstDir)

        if not CreateVolume(options.filer, options.aggr, options.name, options.size):
            print('failed to create volume ' + options.name)
            sys.exit(1)

        try:
            now = datetime.now()
            date = str(now.year) + '.' + str(now.month) + '.' + str(now.day)
            for c in 'exports', 'quotas':
                srcFile = srcDir + '/' + c
                dstFile = dstDir + '/' + c + '.' + options.filer + '.' + date
                UpdateConf(srcFile, dstFile, options.filer, options.name, c, domain)
        except:
            print('backup or update configuration failure')
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
