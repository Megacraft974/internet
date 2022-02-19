import os
import sys
import time
import re
import traceback
from datetime import datetime
from subprocess import PIPE, Popen


def log(*args):
    tmp = []
    for e in args:
        if type(e) == bytes:
            tmp.append(e.decode('utf-8', 'backslashreplace'))
        else:
            tmp.append(str(e))
    txt = ' '.join(tmp)
    print(txt)
    f.write(txt + '\n')
    f.flush()


address = '8.8.8.8'
param = ' -t' if sys.platform == 'win32' else ''
cmd = "ping {}{}".format(address, param)

logfile = os.path.normpath("wifi_log_{}.txt".format(datetime.today().strftime("%Y-%m-%dT%H.%M.%S")))
print("Logfile:", logfile)

process = Popen(cmd, shell=True, stdout=PIPE)
last = (b"", 0)
rep_pattern = re.compile(rb'R\x82ponse de 8.8.8.8\xff: octets=(\d*) temps=(\d*) ms TTL=(\d*)')
with process.stdout as stdout, open(logfile, 'w') as f:
    buf = b""
    while True:
        try:
            buf += stdout.read(5)
            if b"\r\n" in buf:
                out, buf = buf.split(b"\r\n", 1)

                if out == b"Envoi d'une requ\x88te 'Ping'  8.8.8.8 avec 32 octets de donn\x82es\xff:":
                    log("Started at", time.strftime("%H:%M:%S"))
                elif out.startswith(b'R\x82ponse de 8.8.8.8\xff:'):
                    if last[0] != b"":
                        log(last[0], "- de", time.strftime("%H:%M:%S", time.gmtime(last[1])), "à", time.strftime("%H:%M:%S"), "- Duree:", time.strftime("%H:%M:%S", time.gmtime(round(time.time() - last[1], 3))))
                        last = (b"", 0)
                    match = re.findall(rep_pattern, out)
                    if len(match) > 0:
                        octets, temps, ttl = map(int, match[0])
                        print("Ping:", temps, "ms")
                else:
                    if out != last[0]:
                        if last[0] != b"":
                            log(last[0], "- Duree:", time.strftime("%H:%M:%S", time.gmtime(round(time.time() - last[1], 3))))
                        last = (out, time.time())
                        # log(out, "- commencé à", time.strftime("%H:%M:%S"))
        except Exception as e:
            log(e)
            break

print("Stopped at", time.strftime("%H:%M:%S"))