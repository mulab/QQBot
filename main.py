import bisect
import json
import os
import random
import sys

from flask import Flask, jsonify
from flask import request

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

import logging
from logging.handlers import TimedRotatingFileHandler


def create_rotating_log(path='qqbot.log', level=logging.INFO):
    """
    Creates a rotating log
    """
    # logger = logging.getLogger("QQ Bot")
    app.logger.setLevel(level=level)

    # add a rotating handler
    handler = TimedRotatingFileHandler(path,
                                       when="D",
                                       interval=1,
                                       backupCount=5,
                                       encoding='utf8')
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    # return logger


commands = []

plugins = dict()
plugins_names = set()
plugins_priority = []

plugins_reverse = dict()

valid_group = set()
bot_records = set()
admin = 464106231


def load_config(config_file="config.json"):
    global valid_group, bot_records, admin
    if os.path.isfile(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            if config.get("valid_group") is not None:
                valid_group = set(config["valid_group"])
            else:
                valid_group = {290911140, 562286586, 147670798}
            if config.get("bot_records") is not None:
                bot_records = set(config["bot_records"])
            else:
                bot_records = {3071375118, 2119357014, 1429440294}
            if config.get("admin") is not None:
                admin = config["admin"]
            else:
                admin = 464106231


def load_plugins():
    load_plugin("MiaowuBot")
    load_plugin("GirlsDayBot")
    app.logger.info(str(plugins_priority))
    app.logger.info(str(plugins_names))


def load_plugin(plugin_name):
    global plugins, plugins_reverse, commands, plugins_names
    if plugin_name in plugins_names:
        return "Already exist"

    try:
        import importlib
        Plugin_Class = getattr(importlib.import_module(plugin_name), plugin_name)
        plugin = Plugin_Class()
    except Exception as e:
        app.logger.error(e)
        return "Error occurred:" + str(e)

    plugin_commands = plugin.supported_commands()
    for command in plugin_commands:
        if plugins_reverse.get(command) is not None:
            return "Repeated command"
    for command in plugin_commands:
        plugins_reverse[command] = plugin
        commands.append(command)

    if plugins.get(plugin.priority) is None:
        plugins[plugin.priority] = []
        index = bisect.bisect_left(plugins_priority, plugin.priority)
        plugins_priority.insert(index, plugin.priority)
    plugins[plugin.priority].append(plugin)
    plugin.load_data("data/")
    plugins_names.add(plugin_name)
    return "Added"


def backup_config(config_file="config.json"):
    config = dict()
    with open(config_file, 'r') as f:
        config = json.load(f)
    with open(config_file, 'w') as f:
        config['valid_group'] = list(valid_group)
        config['bot_records'] = list(bot_records)
        json.dump(config, f)


@app.route('/msgrcv', methods=['GET', 'POST'])
def message_recieved():
    content = request.json
    if content['post_type'] == 'event':
        print(content)
        return ''
    if content['type'] == 'group_message':
        gnumber = content['group_uid']
        sender = content['sender_uid']
        if gnumber not in valid_group:
            return ''
        if sender in bot_records:
            return ''
        message_content = content['content']
        if message_content.startswith('@miaowu'):
            command = message_content[7:].strip()
            for t in commands:
                if command.startswith(t):
                    plugin = plugins_reverse[t]
                    reply = plugin.command_received(t, command[len(t):], content)
                    if reply != '':
                        return jsonify({"reply": reply})
        for priority in plugins_priority:
            possible_plugins = plugins[priority]
            replys = []
            for plugin in possible_plugins:
                reply = plugin.message_received(content)
                if reply != '':
                    replys.append(reply)
            if len(replys) == 1:
                return jsonify({"reply": replys[0]})
            elif len(replys) > 0:
                return jsonify({"reply": random.choice(replys)})
        return ''
    elif content['type'] == 'message':
        if content['sender_uid'] == admin:
            reply = handle_admin_command(content['content'])
            return jsonify({"reply": reply})


def handle_admin_command(message=""):
    try:
        if message.startswith("!addbot"):
            qq = message[len('!addbot'):].strip()
            bot_records.add(int(qq))
            return 'Done! Add {qq} as bot!' % int(qq)
        if message.startswith("!load"):
            plugin_name = message[len('!addbot'):].strip()
            return load_plugin(plugin_name)
    except Exception:
        return 'Error!'
    return 'not recognized command'


def will_exit(signum, frame):
    backup_config()
    for p, plugin_array in plugins.items():
        for plugin in plugin_array:
            plugin.exit()
    sys.exit(0)


if __name__ == '__main__':
    import signal

    signal.signal(signal.SIGINT, will_exit)
    signal.signal(signal.SIGTERM, will_exit)
    create_rotating_log('logs/qqbot.log')
    load_config()
    load_plugins()

    app.run(host='0.0.0.0', port=8888)
