#!/usr/bin/python3.3

import os
import subprocess
import sys
import re
import time
from optparse import OptionParser

def SubmitJob(queueName, homePath):
    codePath = homePath + '/codebase/KK.' + queueName + '/alps'
    if not os.path.exists(codePath):
        print(codePath + ' : No such file or directory')
        sys.exit(1)
    cmd = '. /etc/bash.bashrc && ccache -C && ' + \
            'cd ' + codePath + ' && ' + \
            queueName + ' /usr/bin/time -f %e "./mk new"'
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    p.wait()
    x = re.compile('^(\d+\.\d+)\s+$')
    if p.returncode == 0:
        for i in p.stdout.readlines():
            i = i.decode()
            if x.search(i):
                break
        else:
            return None
    return float(i) / 60.0

def IsRunning(queueName):
    cmd = '. /etc/bash.bashrc && bjobs -r'
    p = subprocess.Popen(cmd, shell = True,
            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        if out and re.search(queueName, out.decode()):
            return True
    return False

def UpdateElapsedTime(queueName, homePath, elapsedTime):
    resultPath = homePath + '/result.txt'
    label = queueName + '_Time_Mins='
    pattern = label + '(\d+\.\d+|None)'
    x = re.compile(pattern)
    if not os.path.isfile(resultPath):
        open(resultPath, 'a').close()
    s = open(resultPath).read()
    if not x.search(s):
        f = open(resultPath, 'a')
        f.write(label + 'None\n')
        f.close()
    s = open(resultPath).read()
    s = s.replace(x.search(s).group(1), elapsedTime)
    f = open(resultPath, 'w')
    f.write(s)
    f.close()

if __name__ == '__main__':
    parser = OptionParser(usage = 'Usage: %prog [-a|-m]')
    parser.add_option('-a', '--androidq', action = 'store_true',
            help = 'submit the job to android queue')
    parser.add_option('-m', '--mosesq', action = 'store_true',
            help = 'submit the job to mosesq queue')
    (options, args) = parser.parse_args()
    homePath = os.environ['HOME']
    if len(sys.argv) == 1 or len(args) != 0:
        parser.print_help()
        sys.exit(1)
    elif options.androidq and options.mosesq:
        parser.error("options -a and -m are mutually exclusive")
    elif options.androidq and not IsRunning('androidq'):
		pass
        #elapsedTime = str(SubmitJob('androidq', homePath))
        #UpdateElapsedTime('androidq', homePath, elapsedTime)
    elif options.mosesq and not IsRunning('mosesq'):
        pass
        #elapsedTime = str(SubmitJob('mosesq', homePath))
        #UpdateElapsedTime('mosesq', homePath, elapsedTime)
