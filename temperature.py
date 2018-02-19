import redis
import time
import requests

rooms = {
    "bedroom": {
        "name": "bedroom",
        "url": "http://thermostatbed.local/",
        "target_temp": 15,
        "room": 3,
        "device": 1
    },
    "living_room": {
        "name": "living_room",
        "url": "http://thermostatlivingroom.local/",
        "target_temp": 15,
        "room": 2,
        "device": 3
    }
}

def do_action(room, device, action):
    print "Asked to set room %s, device %s, action %s" % (room, device, action)
    url = "http://localhost/action?room=%s&device=%s&action=%s" % (room, device, action)
    print url
    requests.get(url, timeout=5)

def get_temp(url):
    try:
        result = requests.get(url)
        print "got temp:", result.text
        return int(result.text)
    except:
        return None

def do_temp(room, room_name):
    print "Trying to sort temp for", room_name
    temp = get_temp(room['url'])
    if temp is None:
        print "Failed to get %s temp, don't know what to do" % room_name
        return
    else:
        print room_name, temp
        print "Desired:", room['target_temp']
        if temp > room['target_temp']:
            do_action(room=room['room'], device=room['device'], action="off")
        elif temp < room['target_temp']:
            do_action(room=room['room'], device=room['device'], action="on")

while True:
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    print "* Starting loop"
    for room_name, room in rooms.iteritems():
        try:
            redis_target_temp = r.get("target_temp_"+room_name)
            if redis_target_temp is not None:
                redis_target_temp = int(redis_target_temp)
                rooms[room_name]['target_temp'] = redis_target_temp
        except: pass

        print "* Sorting", room_name
        try:
            do_temp(room, room_name)
        except Exception as e:
            print "Skipping exception:", str(e)

    print
    print
    time.sleep(60)
