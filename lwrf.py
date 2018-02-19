from flask import Flask, render_template, request
import redis
from socket import *
import threading
import json
import sys
import os
import time

r = redis.StrictRedis(host='localhost', port=6379, db=0)

udp_send_socket = socket(AF_INET, SOCK_DGRAM)
udp_send_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

# only run this single threaded so that IDs don't collide
TRANSACTION_ID = 101

app = Flask(__name__)


@app.route('/')
def route_slash():
    states = all_states()
    return render_template('slash', states=states, current_temps=current_temps(), targets=targets())


@app.route('/state')
def route_state():
    return json.dumps(all_states())

@app.route('/target')
def target():
    room = request.args.get('room')
    temp = request.args.get('temp')
    result = r.set('target_temp_'+room, temp)
    return "tried?"

@app.route('/action')
def send():
    room = request.args.get('room')
    device = request.args.get('device')
    action = request.args.get('action')

    global TRANSACTION_ID
    TRANSACTION_ID += 1

    # TODO: log here when we try to set things

    if action == "on":
        action = "F1"
    elif action == "off":
        action = "F0"
    elif action == "dimmer":
        percent = int(sys.argv[3])
        amount = str(int(percent / 3)-1)
        action = "FdP"+amount
    else:
        return "Unknown action"

    command = "R%sD%s%s" % (str(room), str(device), action)
    print command
    sendit(command)
    # udp_send_socket.sendto(str(TRANSACTION_ID)+',!'+command+'|', ('255.255.255.255', 9760))
    # udp_send_socket.sendto('101,!R2D3F1|', ('255.255.255.255', 9760))

    retries = 0
    while True:
        if retries == 10:
            return "May have failed to send, didn't get a reply"
        status = r.get('transaction_'+str(TRANSACTION_ID))
        if status is None:
            retries += 1
            time.sleep(0.02)
        else:
            return status


def sendit(command):
    udp_send_socket.sendto(str(TRANSACTION_ID)+',!'+command+'|', ('255.255.255.255', 9760))

def register():
    udp_send_socket.sendto(str(TRANSACTION_ID)+',!F*p', ('255.255.255.255', 9760))

def get_hub():
    udp_send_socket.sendto(str(TRANSACTION_ID)+',@H', ('255.255.255.255', 9760))

def all_states():
    output = {}
    keys = r.keys('state_*')
    for key in keys:
        device = key.replace('state_', '')
        output[device] = r.get(key)
    return output

def current_temps():
    output = {}
    keys = r.keys('current_temp_*')
    for key in keys:
        device = key.replace('current_temp_', '')
        output[device] = r.get(key)
    return output

def targets():
    output = {}
    keys = r.keys('target_temp_*')
    for key in keys:
        device = key.replace('target_temp_', '')
        output[device] = r.get(key)
    return output

def udp_listen_thread():
    transaction_redis_timeout = 10
    print "listen_thread"
    udp_listen_socket = socket(AF_INET, SOCK_DGRAM)
    udp_listen_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    udp_listen_socket.bind(("", 9761))
    print "going into listen while true loop"
    # check ^
    while True:
        m = udp_listen_socket.recvfrom(1024)
        print "Got packet"
        message = m[0]
        print message

        if message[0] == '*':
            print "GOT JSON PACKET?"
            print message
            json_data = message[2:]
            print json_data
            data = json.loads(json_data)
            state_key = 'state_R'+str(data['room'])+'D'+str(data['dev'])
            state = data['fn']
            print "Setting state: ", state_key, state
            r.set(state_key, state)
        else:
            print message
            transaction_id = message.split(',', 1)[0]
            state = message.split(',', 1)[1]
            # TODO: don't timeout errors?
            # ERROR example: 112,ERR,6,"Transmit fail"
            r.setex('transaction_'+transaction_id, transaction_redis_timeout, state)


if __name__ == "__main__":
    try:
        pid = os.fork()
    except OSError:
        exit("Could not create a child process")

    if pid == 0:
        print "in pid 0"
        udp_listen_thread()

    else:
        register()
        time.sleep(1)
        get_hub()
        time.sleep(1)
        app.run(debug=False, host="0.0.0.0", port=80)
