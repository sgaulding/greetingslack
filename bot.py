import websocket
import json
import requests
import urllib
import os
import sys
import logging


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# Suppress InsecureRequestWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

###VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU#####
try:
    MESSAGE = os.environ['WELCOME_MESSAGE']
    TOKEN = os.environ['SLACK_TOKEN']
    UNFURL = os.environ['UNFURL_LINKS']
    DEBUG_CHANNEL_NAME = os.environ.get('DEBUG_CHANNEL_NAME', False)
    WELCOME_MESSAGE_CHANNEL_NAME = os.environ['ADD-MESSAGE-TO-CHANNEL']
except:
    MESSAGE = 'Manually set the Message if youre not running through heroku or have not set vars in ENV'
    TOKEN = 'Manually set the API Token if youre not running through heroku or have not set vars in ENV'
    UNFURL = 'FALSE'
    WELCOME_MESSAGE_CHANNEL_NAME = 'general'


###############################################################

def get_channel_id_by_name(name):
    channels = requests.get("https://slack.com/api/channels.list?token=" + TOKEN)
    channels = channels.json()
    channels = channels['channels']
    channel_id = ''
    for channel in channels:
        if channel['name'].lower() == name.lower():
            channel_id = channel['id']
            break
    return channel_id

def is_team_join(msg):
    return msg['type'] == "team_join"

def is_debug_channel_join(msg):
    return msg['type'] == "member_joined_channel" and msg['channel']['name'] == DEBUG_CHANNEL_NAME and msg['channel_type'] == 'C'

def parse_join(message):
    m = json.loads(message)
    logging.debug(m)
    if is_team_join(m) or is_debug_channel_join(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        logging.debug(m)
        x = requests.get("https://slack.com/api/im.open?token="+TOKEN+"&user="+user_id)
        x = x.json()
        x = x["channel"]["id"]
        logging.debug(x)

        data_to_user = {
                'token': TOKEN,
                'channel': x,
                'text': MESSAGE,
                'parse': 'full',
                'as_user': 'true',
                }

        data_to_channel = {
                'token': TOKEN,
                'channel': get_channel_id_by_name(WELCOME_MESSAGE_CHANNEL_NAME),
                'text': "Welcome " + m["user"],
                'parse': 'full',
                'as_user': 'true',
                }

        logging.debug(data_to_user)

        if UNFURL.lower() == "false":
            data_to_user = data_to_user.update({'unfurl_link': 'false'})
            data_to_channel = data_to_user.update({'unfurl_link': 'false'})

        post_to_user = requests.post("https://slack.com/api/chat.postMessage", data=data_to_user)
        post_to_channel = requests.post("https://slack.com/api/chat.postMessage", data=data_to_channel)

        logging.debug('\033[91m' + "HELLO SENT TO " + m["user"]["id"] + '\033[0m')
        logging.debug(post_to_user.json())
        logging.debug(post_to_channel.json())

# Connects to Slacks and initiates socket handshake
def start_rtm():
    r = requests.get("https://slack.com/api/rtm.start?token=" + TOKEN, verify=False)
    r = r.json()
    logging.info(r)
    r = r["url"]
    return r

def on_message(ws, message):
    parse_join(message)

def on_error(ws, error):
    logging.error("SOME ERROR HAS HAPPENED: " + error)

def on_close(ws):
    logging.info('\033[91m'+"Connection Closed"+'\033[0m')

def on_open(ws):
    logging.info("Connection Started - Auto Greeting new joiners to the network")

if __name__ == "__main__":
    r = start_rtm()
    ws = websocket.WebSocketApp(r, on_message=on_message, on_error=on_error, on_close=on_close)
    # ws.on_open
    ws.run_forever()

