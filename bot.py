import json
import logging
import os
import sys

import requests
import websocket

from requests.packages.urllib3.exceptions import InsecureRequestWarning

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# *****VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU*****
try:
    MESSAGE = os.environ['PERSONAL_WELCOME_MESSAGE_TO_USER']
    TOKEN = os.environ['SLACK_TOKEN']
    UNFURL = os.environ['UNFURL_LINKS']
    LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')
    DEBUG_CHANNEL_NAME = os.environ.get('DEBUG_CHANNEL_NAME', False)
    DEBUG_CHANNEL_ID = os.environ.get('DEBUG_CHANNEL_ID', False)
    WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME = os.environ['WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME']
    WELCOME_USER_TO_GROUP_IN_CHANNEL_ID = os.environ.get('WELCOME_USER_TO_GROUP_IN_CHANNEL_ID', False)
except KeyError:
    MESSAGE = 'Manually set the Message if youre not running through heroku or have not set vars in ENV'
    TOKEN = 'Manually set the API Token if youre not running through heroku or have not set vars in ENV'
    UNFURL = 'FALSE'
    DEBUG_CHANNEL_NAME = False
    DEBUG_CHANNEL_ID = False
    WELCOME_USER_TO_GROUP_IN_CHANNEL_ID = False
    WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME = False


###################################################################


def get_channel_id_by_name(name):
    if name.isspace():
        return False

    channel_response = requests.get("https://slack.com/api/channels.list?token=" + TOKEN).json()
    logging.debug(channel_response)
    channels = channel_response['channels']
    channel_id = ''
    for channel in channels:
        if channel['name'].lower() == name.lower():
            channel_id = channel['id']
            break
    return channel_id


def is_team_join(msg):
    return msg['type'] == "team_join"


def is_debug_channel_join(msg):
    if not DEBUG_CHANNEL_NAME:
        return False

    global DEBUG_CHANNEL_ID
    if not DEBUG_CHANNEL_ID:
        DEBUG_CHANNEL_ID = get_channel_id_by_name(DEBUG_CHANNEL_NAME)

    return msg['type'] == "member_joined_channel" and msg['channel'] == DEBUG_CHANNEL_ID and msg['channel_type'] == 'C'


def get_user_name_from_id(user_id):
    if user_id.isspace():
        return 'New Member'

    data = {
        'token': TOKEN,
        'user': user_id
    }

    user_response = requests.post("https://slack.com/api/users.info", data=data).json()
    logging.debug(user_response)
    return user_response['user']['name']


def parse_join(message):
    m = json.loads(message)
    if is_team_join(m) or is_debug_channel_join(m):
        user_id = m["user"]["id"] if is_team_join(m) else m["user"]
        logging.debug(m)
        x = requests.get("https://slack.com/api/im.open?token=" + TOKEN + "&user=" + user_id)
        x = x.json()
        x = x["channel"]["id"]
        logging.debug(x)

        data_to_user = {
            'token': TOKEN,
            'channel': x,
            'text': MESSAGE,
            'parse': 'full',
            'as_user': 'true',
            'unfurl_link': UNFURL.lower()
        }

        logging.debug(data_to_user)
        post_to_user = requests.post("https://slack.com/api/chat.postMessage", data=data_to_user)
        logging.debug('\033[91m' + "HELLO SENT TO " + user_id + '\033[0m')
        logging.debug(post_to_user.json())

        global WELCOME_USER_TO_GROUP_IN_CHANNEL_ID
        if not WELCOME_USER_TO_GROUP_IN_CHANNEL_ID:
            welcome_to_group_channel_id = get_channel_id_by_name(WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME)
            WELCOME_USER_TO_GROUP_IN_CHANNEL_ID = welcome_to_group_channel_id
        else:
            welcome_to_group_channel_id = WELCOME_USER_TO_GROUP_IN_CHANNEL_ID

        if welcome_to_group_channel_id != '':
            user_name = get_user_name_from_id(user_id)

            data_to_channel = {
                'token': TOKEN,
                'channel': welcome_to_group_channel_id,
                'text': "Welcome @" + user_name,
                'parse': 'full',
                'as_user': 'true',
                'unfurl_link': UNFURL.lower()
            }

            post_to_channel = requests.post("https://slack.com/api/chat.postMessage", data=data_to_channel)
            logging.debug(post_to_channel.json())


# Connects to Slacks and initiates socket handshake
def start_rtm():
    start_request = requests.get("https://slack.com/api/rtm.start?token=" + TOKEN, verify=False)
    start_request = start_request.json()
    logging.info(start_request)
    start_request = start_request["url"]
    return start_request


def on_message(ws, message):
    parse_join(message)


def on_error(ws, error):
    logging.error("SOME ERROR HAS HAPPENED: " + error)


def on_close(ws):
    logging.info('\033[91m' + "Connection Closed" + '\033[0m')


def on_open(ws):
    logging.info("Connection Started - Auto Greeting new joiners to the network")


def set_logging_level():
    logging_level = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'notset': logging.NOTSET
    }
    level = logging_level.get(LOGGING_LEVEL.lower(), logging.INFO)
    logging.getLogger().setLevel(level)


if __name__ == "__main__":
    set_logging_level()
    r = start_rtm()
    web_socket_app = websocket.WebSocketApp(r, on_message=on_message, on_error=on_error, on_close=on_close)
    # web_socket_app.on_open
    web_socket_app.run_forever()
