import bisect
import json
import logging
import os
import random
import sys
from logging.handlers import TimedRotatingFileHandler

import redis
import requests
from flask import Flask, jsonify
from flask import request

from plugin import Plugin

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


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


prefix = ""

commands = []

plugins = dict()
plugins_names = set()
plugins_priority = []

plugins_reverse = dict()

pool = None
database = None
webqq = None
weixin = None
weixin_mapping = dict()
weixin_group_mapping = dict()


def load_config(config_file="config.json"):
    global database, pool, prefix, webqq
    global weixin, weixin_mapping
    if os.path.isfile(config_file):
        with open(config_file, 'r', encoding='utf8') as f:
            config = json.load(f)
            if config.get("webqq") is not None:
                webqq = config["webqq"]
            else:
                webqq = "127.0.0.1:5000"
            if config.get("redis") is not None:
                pool = redis.ConnectionPool(host=config.get("redis"), port=6379, db=0)
                database = redis.StrictRedis(connection_pool=pool)
            if config.get("prefix") is not None:
                prefix = config.get("prefix")
            else:
                prefix = "@miaowu"
            if config.get("weixin") is not None:
                weixin = config["weixin"]
            if config.get("weixin_mapping") is not None:
                weixin_mapping = config.get("weixin_mapping")
            else:
                weixin_mapping = dict()


class BasicBot(Plugin):
    command_description = ""
    priority = 100

    def load_data(self, **kwargs):
        return

    def supported_commands(self):
        return ["!help", "!cmd"]

    def message_received(self, message):
        return ''

    def command_received(self, command, content, messageInfo):
        global plugins
        if command == '!help':
            name = content.strip()
            if name == '':
                return "Loaded Plugins:\n" + (", ".join(plugins_names))
            if name == "BasicBot":
                return ''
            if name in plugins_names:
                for priority, ps in plugins.items():
                    for p in ps:
                        if type(p).__name__ == name:
                            return p.command_description
        elif command == '!cmd':
            name = content.strip()
            if name == '':
                return "All Commands:\n" + "\n".join(plugins_reverse.keys())
            if plugins_reverse.get(name) is not None:
                p = plugins_reverse[name]
                return p.command_description
        return ''

    def exit(self):
        return


def load_plugins():
    global plugins, plugins_reverse, commands, plugins_names
    basic_bot = BasicBot()
    plugin_commands = basic_bot.supported_commands()
    for command in plugin_commands:
        plugins_reverse[command] = basic_bot
        commands.append(command)
    plugins[basic_bot.priority] = [basic_bot]
    plugins_names.add("BasicBot")

    load_plugin("MiaowuBot")
    load_plugin("RollBot")
    # load_plugin("GirlsDayBot")
    app.logger.info(str(plugins_priority))
    app.logger.info(str(plugins_names))


def load_plugin(plugin_name):
    global plugins, plugins_reverse, commands, plugins_names, pool, webqq
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
    plugin.load_data("data/", redis_pool=pool, webqq=webqq)
    plugins_names.add(plugin_name)
    return "Added"


@app.route('/msgrcv', methods=['GET', 'POST'])
def message_recieved():
    content = request.json
    if content['post_type'] == 'event':
        # print(content)
        return ''
    if content['post_type'] != 'receive_message':
        return ''
    if content['sender'] == '昵称未知' and content['sender_uid'] is None:
        return ''
    if content['type'] == 'group_message':
        gnumber = content['group_uid']
        gid = content['group_id']
        if gnumber is None:
            if content['group'] is None:
                return ''
            gname = content['group']
            for n in weixin_mapping:
                if gname.startswith(n):
                    content['group_uid'] = weixin_mapping[n]
                    gnumber = weixin_mapping[n]
        sender = content['sender_uid']
        if not database.sismember('valid_group', gnumber):
            return ''
        if database.sismember('bot_records', sender):
            return ''
        message_content = content['content']
        if message_content is None:
            return ''
        if message_content.startswith(prefix):
            command_part = message_content[len(prefix):].strip()
            command = command_part.split(' ')[0]
            for t in commands:
                if command == t:
                    plugin = plugins_reverse[t]
                    reply = plugin.command_received(t, command_part[len(t):], content)
                    if reply != '':
                        return handle_return_message(reply, gnumber, gid)
        for priority in plugins_priority:
            possible_plugins = plugins[priority]
            replys = []
            for plugin in possible_plugins:
                reply = plugin.message_received(content)
                if reply != '':
                    replys.append(reply)
            if len(replys) == 1:
                return handle_return_message(replys[0], gnumber, gid)
            elif len(replys) > 0:
                return handle_return_message(random.choice(replys), gnumber, gid)
        return ''
    elif content['type'] == 'friend_message':
        if database.sismember('admin', content['sender_uid']):
            reply = handle_admin_command(content['content'])
            return jsonify({"reply": reply})
    return ''


@app.route('/wxrcv', methods=['GET', 'POST'])
def wx_message_recieved():
    global weixin_group_mapping
    content = request.json
    # print(content)
    if content['post_type'] == 'event':
        print(content)
        return ''
    if content['post_type'] != 'receive_message':
        return ''
    if content['type'] == 'group_message':
        gnumber = content['group_id']
        sender = content['sender_uid']
        if weixin_group_mapping.get(gnumber) is None:
            group_name = content['group']
            for group_prefix in weixin_mapping:
                if group_name.startswith(group_prefix):
                    group_uid = weixin_mapping[group_prefix]
                    for (key, value) in weixin_group_mapping.items():
                        if value == group_uid:
                            del weixin_group_mapping[key]
                            break
                    weixin_group_mapping[gnumber] = group_uid
                    break
            return ''
        else:
            content['group_uid'] = weixin_group_mapping[gnumber]
        message_content = content['content']
        if message_content.startswith('!'):
            command_part = message_content.strip()
            command = command_part.split(' ')[0]
            for t in commands:
                if command == t:
                    plugin = plugins_reverse[t]
                    if not plugin.weixin_enabled():
                        continue
                    reply = plugin.command_received(t, command_part[len(t):], content)
                    if reply != '':
                        return wx_handle_return_message(reply, gnumber)
        for priority in plugins_priority:
            possible_plugins = plugins[priority]
            replys = []
            for plugin in possible_plugins:
                if not plugin.weixin_enabled():
                    continue
                reply = plugin.message_received(content)
                if reply != '':
                    replys.append(reply)
            if len(replys) == 1:
                return wx_handle_return_message(replys[0], gnumber)
            elif len(replys) > 0:
                return wx_handle_return_message(random.choice(replys), gnumber)
        return ''
    return ''


def handle_return_message(reply: str, uid, id=None):
    global webqq
    lines = reply.splitlines()
    if id is None:
        return ''
    if len(lines) > 20:
        for i in range(0, len(lines), 20):
            temp_reply = '\n'.join(lines[i:i + 20])
            requests.get("http://{}/openqq/send_group_message".format(webqq),
                         params={'id': id, 'content': temp_reply})
        return ''
    else:
        return jsonify({"reply": reply})


def wx_handle_return_message(reply: str, uid):
    return jsonify({"reply": reply})


def handle_admin_command(message=""):
    try:
        if message.startswith("!addbot"):
            qq = message[len('!addbot'):].strip()
            database.sadd('bot_records', qq)
            return 'Done! Add {qq} as bot!' % int(qq)
        if message.startswith("!load"):
            plugin_name = message[len('!load'):].strip()
            return load_plugin(plugin_name)
        if message.startswith("!relogin"):
            requests.get("http://{}/openqq/relogin".format(webqq))
            return "Request sent"
    except Exception:
        return 'Error!'
    return 'not recognized command'


def will_exit(signum, frame):
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
