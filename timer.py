import redis
import time
import requests
import sys
import json
import time

minute = time.strftime("%H%M")
print minute

r = redis.StrictRedis(host='localhost', port=6379, db=0)
timers = r.keys("timer_*")
for timer in timers:
    try:
        data = json.loads(r.get(timer))
        print data
        if data['time'] != minute:
            print "skipping timer with wrong time"
            continue
        print "Need to apply the timer!"
        r.set("target_temp_%s" % data['room'], "%s" % data['target'])
    except:
        pass

