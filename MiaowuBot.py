import os
import random
import json
from plugin import Plugin


class MiaowuBot(Plugin):
    command_description = "Miaowu Bot Usage:" \
               "!add    trigger#reply" \
               "!del    trigger#reply" \
               "!list   trigger"
    priority = 80

    def __init__(self):
        self.reply_data = dict()

    def load_data(self, data_path = ""):
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
            if self.reply_data[gnumber].get(trigger, None) is None:
                self.reply_data[gnumber][trigger] = []
            self.reply_data[gnumber][trigger].append(r)
            return 'Done!'
        elif command == '!del':
            del_message = content.strip().split('#', 1)
            if len(del_message) < 2:
                return ''
            trigger = del_message[0].strip()
            r = del_message[1].strip()

            if self.reply_data[gnumber].get(trigger, None) is None:
                return ''
            if r in self.reply_data[gnumber][trigger]:
                self.reply_data[gnumber][trigger].remove(r)
                if len(self.reply_data[gnumber][trigger]) == 0:
                    del self.reply_data[gnumber][trigger]
                return 'Done!'
        elif command == '!list':
            trigger = content.strip()
            if self.reply_data[gnumber].get(trigger, None) is None:
                return 'No records for ' + trigger
            reply = "List " + trigger + " :\n" + '\n'.join(self.reply_data[gnumber][trigger])
            return reply
        return ''

    def message_received(self, message):
        gnumber = message['group_uid']
        message_content = message['content']
        if self.reply_data.get(gnumber) is None:
            self.reply_data[gnumber] = dict()
        for key in self.reply_data[gnumber].keys():
            if key in message_content:
                all_reply = self.reply_data[gnumber][key]
                if len(all_reply) > 0:
                    reply = random.choice(all_reply)
                    return reply
        return ''

    def exit(self):
        with open(self.filepath, 'w', encoding='utf8') as f:
            json.dump(self.reply_data, fp=f, ensure_ascii=False)
        return "bak finished"