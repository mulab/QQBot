import redis
import time

import requests

from plugin import Plugin


class ZaoBot(Plugin):
    command_description = "ZanBot Usage:\n" \
                          "!zao\n" \
                          "!zaoguys"

    priority = 50

    def in_this_day(self, t: float):

        now = time.time()
        if self.day_end_time is not None and now < self.day_end_time:
            return self.day_end_time > t >= self.day_start_time

        x = self.day_start - 8
        while x < 0:
            x += 24
        a = now - x * 60 * 60
        reminder = a % (24 * 60 * 60)
        self.day_start_time = now - reminder
        self.day_end_time = self.day_start_time + 24 * 60 * 60
        return self.day_end_time > t >= self.day_start_time

    def __init__(self):
        self.database = redis.StrictRedis()  # None
        self.day_start = 0
        self.day_start_time = None
        self.day_end_time = None
        self.last_update = None
        self.webqq = "127.0.0.1:5000"

    def load_data(self, data_path="", redis_pool=None, webqq=""):
        self.webqq = webqq
        self.database = redis.StrictRedis(connection_pool=redis_pool)
        if self.database.exists('zao:config'):
            self.day_start = self.database.hget('zao:config', 'day_start')
            if self.day_start is None:
                self.day_start = 5
            else:
                self.day_start = int(self.day_start)
            self.last_update = self.database.hget('zao:config', 'last_update')
            if self.last_update is not None:
                if not self.in_this_day(float(self.last_update)):
                    self.database.delete('zao:data')
                    self.database.delete('zao:userinfo')
            else:
                self.last_update = float(self.last_update)
        else:
            self.database.hset('zao:config', 'day_start', 5)
        return

    def check_last_update(self):
        if self.last_update is not None:
            if not self.in_this_day(float(self.last_update)):
                self.database.delete('zao:data')
                self.database.delete('zao:userinfo')

    def supported_commands(self):
        return ['!zao', '!zaoguys']

    def message_received(self, message):
        self.check_last_update()
        qq = message['sender_uid']
        if self.database.zscore('zao:data', qq) is None:
            #
            t = time.time()
            self.database.zadd('zao:data', t, str(qq))
            self.database.hset('zao:config', 'last_update', t)
            self.last_update = t
            self.get_user_name(qq, message['group_uid'])
        return ''

    def command_received(self, command, content, messageInfo):
        self.check_last_update()
        if command == '!zao':
            qq = messageInfo['sender_uid']
            t = self.database.zscore('zao:data', qq)
            if t is None:
                now = time.time()
                self.database.zadd('zao:data', now, str(qq))
                name = self.get_user_name(qq, messageInfo['group_uid'])
                self.database.hset('zao:config', 'last_update', now)
                if name is not None:
                    return "{}, 早安".format(name)
                else:
                    return "QQ {}, 早安".format(qq)
            else:
                ts = time.strftime('%H:%M', time.localtime(t))
                return "不早了, 你在{}时说过话了".format(ts)
        elif command == '!zaoguys':
            all = self.database.zrange('zao:data', 0, -1, withscores=True)
            if len(all) == 0:
                return "o<<(≧口≦)>>o 还没人起床"
            message = []
            for index, data in enumerate(all):
                qq = data[0].decode()
                t = data[1]
                ts = time.strftime('%H:%M', time.localtime(t))
                name = self.get_user_name(qq, messageInfo['group_uid'])
                if name is None:
                    name = "({})".format(qq)
                message.append("{}. {} , wake up at {}".format(index, name, ts))
            print(all)
            return '\n'.join(message)
        return ''

    def get_user_name(self, qq, group=None):
        name = self.database.hget('zao:userinfo', qq)
        if name is not None:
            return name.decode()

        if group is None:
            return None

        a = requests.get("http://{}/openqq/search_group".format(self.webqq), params={'uid': group})
        group_infos = a.json()
        try:
            if len(group_infos) > 0:
                members = group_infos[0]['member']
                for member in members:
                    if member.get('uid') is None:
                        continue
                    qid = member['uid']
                    if qid == qq:
                        name = member['name']
                        self.database.hset('zao:userinfo', qq, name)
                        return name
                return None
        except KeyError as e:
            print(e)
            print(a.json())
        return None

    def exit(self):
        return
