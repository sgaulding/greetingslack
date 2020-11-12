import json
import logging
import sys

import requests
import websocket


logging.basicConfig(level=logging.DEBUG,
        stream=sys.stdout)

from settings import get_env_variable

logging.basicConfig(level=logging.INFO,
                    stream=sys.stdout,
                    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

###VARIABLES THAT YOU NEED TO SET MANUALLY IF NOT ON HEROKU#####


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

def is_direct_message(msg):
    print(msg)
    is_bot = False
    if 'bot_id' in msg:
        is_bot = True
    return msg['type'] == "message" and msg['channel'][0] == 'D' and not is_bot

def get_display_name(user_id):
    logging.debug('FINDING USER WITH ID'+user_id)
    users = requests.get("https://slack.com/api/users.list?token="+TOKEN)
    users = users.json()

    for item in users['members']:
        if user_id == item['id']:
            return item['real_name']

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
        conversation = requests.post("https://slack.com/api/conversations.open?token=" + TOKEN + "&users=" + user_id,
                          data=None).json()
        conversation_channel = conversation["channel"]["id"]
        logging.debug(conversation_channel)

        data = {
                'token': TOKEN,
                'channel': conversation_channel,
                'text': MESSAGE,
                'parse': 'full',
                'as_user': 'true',
                }
                
        logging.debug(data)
        
            post_to_channel = requests.post("https://slack.com/api/chat.postMessage", data=data_to_channel)
            logging.debug(post_to_channel.json())
            logging.debug('\033[91m' + "WELCOME SENT SENT TO " + user_name + '\033[0m')

        if (UNFURL.lower() == "false"):
          data.update({'unfurl_link': 'false'})

        post_message_response = requests.post("https://slack.com/api/chat.postMessage", data=data)
        logging.debug('\033[91m' + "HELLO SENT TO " + m["user"]["id"] + '\033[0m')

    if is_direct_message(m):
        logging.debug('DM RECEIVED')
        user_id = m["user"]
        user_message = m['text']
        user_message = urllib.quote(user_message)

        # Need to get the display name from the user_id
        real_name = get_display_name(user_id)

        #logging.DEBUG('SENDING MESSAGE: '+user_message+' TO USER '+real_name)
        # Need to send a message to a channel
        requests.get("https://slack.com/api/chat.postMessage?token="+CHANNEL_TOKEN+"&channel="+RESPONSE_CHANNEL+"&text="+user_message+"&as_user=false&username="+real_name)

#Connects to Slacks and initiates socket handshake
def start_rtm():

    r = requests.get("https://slack.com/api/rtm.start?token="+TOKEN, verify=False)
    r = r.json()
    logging.info(r)
    r = r["url"]
    return r


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
    logging.info("Message:" + str(MESSAGE))
    logging.info("Token: " + str(BOT_TOKEN))
    logging.info("Unfer URL: " + str(UNFURL))
    logging.info("Logging Level: " + str(LOGGING_LEVEL))


def log_channel_info():
    logging.info("Debug Channel Name: " + str(DEBUG_CHANNEL_NAME))
    logging.info("Debug Channel ID: " + str(DEBUG_CHANNEL_ID))
    logging.info("Welcome Channel Name: " + str(WELCOME_USER_TO_GROUP_IN_CHANNEL_NAME))
    logging.info("Welcome Channel ID: " + str(WELCOME_USER_TO_GROUP_IN_CHANNEL_ID))


if __name__ == "__main__":
    set_logging_level()
    log_global_variables()
    r = start_rtm()
    log_channel_info()
    web_socket_app = websocket.WebSocketApp(r, on_message=on_message, on_error=on_error, on_close=on_close)
    # web_socket_app.on_open
    web_socket_app.run_forever()
