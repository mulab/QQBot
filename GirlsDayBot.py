import json
import os
import random
import datetime

import math
import pytz

from plugin import Plugin

class GirlsDayBot(Plugin):
    command_description = ""
    priority = 0

    def __init__(self):
        self.filepath = ""
        self.suffix = []
        self.girls = dict()
        self.girls_count = dict()

    def load_data(self, data_path=""):
        self.filepath = os.path.join(data_path, "girls_day_data.json")
        self.girls = dict()
        self.suffix = []
        if os.path.isfile(self.filepath):
            with open(self.filepath, 'r', encoding='utf8') as f:
                temp = json.load(f)

                for key in temp["girls"].keys():
                    self.girls[int(key)] = temp["girls"][key]
                self.suffix = temp["suffix"]
                for key in temp["count"].keys():
                    self.girls_count[int(key)] = int(temp["count"][key])

        return

    def supported_commands(self):
        return []

    def message_received(self, message):
        now = datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        if now.month != 3 or now.day != 7:
            return ''
        gnumber = message['group_uid']
        if int(gnumber) != 147670798:
            return ''

        user_id = message['sender_uid']
        if self.girls.get(user_id) is not None:
            print(user_id, self.girls.get(user_id))
            if self.girls_count.get(user_id) is None:
                self.girls_count[user_id] = 0
            count = self.girls_count[user_id]+1
            self.girls_count[user_id] = count
            thres = math.exp(-float(count)/5)*0.7+0.3
            if random.random() > thres:
                return ''
            suffix = random.choice(self.suffix)
            return self.girls.get(user_id) + "女生节快乐！ "+suffix
        # message_content = message['content']
        # if "今日头条" in message_content:
        #     if "今日头条" in message_content:
        #     return "明天还是女生节！"
        return ''

    def command_received(self, command, content, messageInfo):
        return ''

    def exit(self):
        temp = {"girls":self.girls, "suffix":self.suffix, "count":self.girls_count}
        with open(self.filepath, 'w', encoding='utf8') as f:
            json.dump(temp, fp=f, ensure_ascii=False)
        return

