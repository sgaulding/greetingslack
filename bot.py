import json
import logging
import sys

import requests
import websocket

from requests.packages.urllib3.exceptions import InsecureRequestWarning

from settings import get_env_variable

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# *****VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU*****


MESSAGE = get_env_variable('PERSONAL_WELCOME_MESSAGE_TO_USER',
                           'Manually set the Message if youre not running through heroku or have not set vars in ENV')
BOT_TOKEN = get_env_variable('SLACK_BOT_TOKEN',
                             'Manually set the BOT Token if not running through heroku or have not set vars in ENV')
UNFURL = get_env_variable('UNFURL_LINKS', False)
LOGGING_LEVEL = get_env_variable('LOGGING_LEVEL', 'INFO')
DEBUG_CHANNEL_NAME = get_env_variable('DEBUG_CHANNEL_NAME', False)
DEBUG_CHANNEL_ID = get_env_variable('DEBUG_CHANNEL_ID', False)
WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME = get_env_variable('WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME', False)
WELCOME_USER_TO_GROUP_IN_CHANNEL_ID = get_env_variable('WELCOME_USER_TO_GROUP_IN_CHANNEL_ID', False)


###################################################################


def get_channel_id_by_name(name):
    if not name or name.isspace():
        return False

    channel_id = ''

    channel_list_url = "https://slack.com/api/channels.list?exclude_members=1&token=" + BOT_TOKEN
    channel_list_response = requests.post(channel_list_url).json()
    logging.debug(channel_list_response)
    private_channels = channel_list_response['channels']
    for channel in private_channels:
        if channel['name'].lower() == name.lower():
            channel_id = channel['id']
            break

    if not channel_id:
        channel_private_url = "https://slack.com/api/groups.list?exclude_members=1&exclude_archived=1&token=" + BOT_TOKEN
        channel_private_response = requests.post(channel_private_url).json()
        logging.debug(channel_private_response)
        private_channels = channel_private_response['groups']
        for channel in private_channels:
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
        logging.debug('Test Channel ID: [' + DEBUG_CHANNEL_ID + ']')

    return msg['type'] == "member_joined_channel" and msg['channel'] == DEBUG_CHANNEL_ID \
        and (msg['channel_type'] == 'C' or msg['channel_type'] == 'G')


def get_user_name_from_id(user_id):
    if user_id.isspace():
        return 'New Member'

    data = {
        'token': BOT_TOKEN,
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
        x = requests.get("https://slack.com/api/im.open?token=" + BOT_TOKEN + "&user=" + user_id)
        x = x.json()
        x = x["channel"]["id"]
        logging.debug(x)

        data_to_user = {
            'token': BOT_TOKEN,
            'channel': x,
            'text': MESSAGE,
            'parse': 'full',
            'as_user': 'true',
            'unfurl_link': UNFURL.lower()
        }

        logging.debug(data_to_user)
        post_to_user = requests.post("https://slack.com/api/chat.postMessage", data=data_to_user)
        logging.debug('\033[91m' + "PERSONAL HELLO SENT TO " + user_id + '\033[0m')
        logging.debug(post_to_user.json())

        global WELCOME_USER_TO_GROUP_IN_CHANNEL_ID
        if not WELCOME_USER_TO_GROUP_IN_CHANNEL_ID:
            welcome_to_group_channel_id = get_channel_id_by_name(WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME)
            WELCOME_USER_TO_GROUP_IN_CHANNEL_ID = welcome_to_group_channel_id
            logging.debug('Welcome Group Channel ID: [' + WELCOME_USER_TO_GROUP_IN_CHANNEL_ID + ']')
        else:
            welcome_to_group_channel_id = WELCOME_USER_TO_GROUP_IN_CHANNEL_ID

        if welcome_to_group_channel_id != '':
            user_name = get_user_name_from_id(user_id)

            data_to_channel = {
                'token': BOT_TOKEN,
                'channel': welcome_to_group_channel_id,
                'text': "Welcome @" + user_name,
                'parse': 'full',
                'as_user': 'true',
                'unfurl_link': UNFURL.lower()
            }

            post_to_channel = requests.post("https://slack.com/api/chat.postMessage", data=data_to_channel)
            logging.debug(post_to_channel.json())
            logging.debug('\033[91m' + "WELCOME SENT SENT TO " + user_name + '\033[0m')


# Connects to Slacks and initiates socket handshake
def start_rtm():
    start_request = requests.get("https://slack.com/api/rtm.connect?token=" + BOT_TOKEN, verify=False)
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

    global LOGGING_LEVEL
    level = logging_level.get(LOGGING_LEVEL.lower(), logging.INFO)
    logging.getLogger().setLevel(level)


def log_global_variables():
    logging.debug("Message:" + str(MESSAGE))
    logging.debug("Token: " + str(BOT_TOKEN))
    logging.debug("Unfer: " + str(UNFURL))
    logging.debug("Logging Leve: " + str(LOGGING_LEVEL))

    logging.debug("Debug Channel Name: " + str(DEBUG_CHANNEL_NAME))
    logging.debug("Debug Channel ID: " + str(DEBUG_CHANNEL_ID))
    logging.debug("Welcome Channel Name: " + str(WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME))
    logging.debug("Welcome Channel ID: " + str(WELCOME_USER_TO_GROUP_IN_CHANNEL_ID))


if __name__ == "__main__":
    set_logging_level()
    r = start_rtm()
    web_socket_app = websocket.WebSocketApp(r, on_message=on_message, on_error=on_error, on_close=on_close)
    # web_socket_app.on_open
    log_global_variables()
    web_socket_app.run_forever()
