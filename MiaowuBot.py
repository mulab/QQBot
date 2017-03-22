import os
import random
import json
from plugin import Plugin
import redis


class MiaowuBot(Plugin):
    command_description = "Miaowu Bot Usage:" \
                          "!add    trigger#reply" \
                          "!del    trigger#reply" \
                          "!list   trigger"
    priority = 80

    def __init__(self):
        self.reply_data = dict()
        self.use_redis = False
        self.database = None

    def load_data(self, data_path="", redis_pool=None):
        if redis_pool is not None:
            self.use_redis = True
            self.database = redis.StrictRedis(connection_pool=redis_pool)
            return
        self.filepath = os.path.join(data_path, "reply_data.json")
        self.reply_data = dict()
        if os.path.isfile(self.filepath):
            with open(self.filepath, 'r', encoding='utf8') as f:
                temp = json.load(f)
                for key in temp.keys():
                    self.reply_data[int(key)] = temp[key]
        return

    def supported_commands(self):
        return ['!add', '!del', '!list']

    def command_received(self, command, content, messageInfo):
        gnumber = messageInfo['group_uid']
        if self.reply_data.get(gnumber) is None:
            self.reply_data[gnumber] = dict()
        if command == '!add':
            add_message = content.strip().split('#', 1)
            if len(add_message) < 2:
                print("not enough", add_message)
                return ''
            trigger = add_message[0].strip()
            if len(trigger) < 2:
                return 'Trigger must > 2'
            r = add_message[1].strip()
            print("add", trigger, r)
            return self.add_trigger(gnumber, trigger, r)
        elif command == '!del':
            del_message = content.strip().split('#', 1)
            if len(del_message) < 2:
                return ''
            trigger = del_message[0].strip()
            r = del_message[1].strip()

            return self.del_trigger(gnumber, trigger, r)
        elif command == '!list':
            trigger = content.strip()
            messages = self.get_trigger_message(gnumber, trigger)
            if messages is None or len(messages) == 0:
                return 'No records for ' + trigger
            reply = "List " + trigger + " :\n" + '\n'.join(messages)
            return reply
        return ''

    def message_received(self, message):
        gnumber = message['group_uid']
        message_content = message['content']
        for key in self.get_trigger(gnumber):
            if key in message_content:
                return self.get_ramdom_reply(gnumber, key)
        return ''

    def exit(self):
        if self.use_redis:
            return "Use redis, no need for backup"
        else:
            with open(self.filepath, 'w', encoding='utf8') as f:
                json.dump(self.reply_data, fp=f, ensure_ascii=False)
            return "backup finished"


    def get_trigger(self, group_id):
        if self.use_redis:
            return list(map(bytes.decode, self.database.smembers("miaowu:{}".format(group_id))))
        else:
            if self.reply_data[group_id] is None:
                self.reply_data[group_id] = dict()
            return self.reply_data[group_id]

    def get_trigger_message(self, group_id, trigger):
        if self.use_redis:
            return list(map(bytes.decode, self.database.smembers("miaowu:{}:{}".format(group_id, trigger))))
        else:
            if self.reply_data[group_id] is None:
                self.reply_data[group_id] = dict()
            return self.reply_data[group_id][trigger]

    def get_ramdom_reply(self, group_id, trigger):
        if self.use_redis:
            return self.database.srandmember("miaowu:{}:{}".format(group_id, trigger)).decode()
        else:
            all_reply = self.reply_data[group_id][trigger]
            if len(all_reply) > 0:
                reply = random.choice(all_reply)
                return reply

    def add_trigger(self, group_id, trigger, message):
        if self.use_redis:
            self.database.sadd("miaowu:{}".format(group_id), trigger)
            if self.database.sadd("miaowu:{}:{}".format(group_id, trigger), message) == 1:
                return "Added"
            else:
                return "Reply already exists"
        else:
            if self.reply_data[group_id].get(trigger, None) is None:
                self.reply_data[group_id][trigger] = []
            self.reply_data[group_id][trigger].append(message)
            return 'Added'

    def del_trigger(self, group_id, trigger, message):
        if self.use_redis:
            if not self.database.sismember("miaowu:{}".format(group_id), trigger):
                return 'Trigger not exist'
            reply = ""
            id_trigger_key = "miaowu:{}:{}".format(group_id, trigger)
            if self.database.srem(id_trigger_key, message) == 1:
                reply = "Removed"
            else:
                reply = "Reply not exist"
            if self.database.scard(id_trigger_key) == 0:
                self.database.delete(id_trigger_key)
                self.database.srem("miaowu:{}".format(group_id), trigger)
            return reply
        else:
            if self.reply_data[group_id].get(trigger, None) is None:
                return 'Trigger not exist'
            if message in self.reply_data[group_id][trigger]:
                self.reply_data[group_id][trigger].remove(message)
                if len(self.reply_data[group_id][trigger]) == 0:
                    del self.reply_data[group_id][trigger]
                    return "Removed"
                return 'Reply not exist'
