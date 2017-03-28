import os
import random
import json
from plugin import Plugin
import redis
import requests


class YanBot(Plugin):
    command_description = "YanBot Usage:\n" \
                          "!smoke <QQ>\n" \
                          "!smoke @群昵称 (可能误伤)\n" \
                          "!roll"
    priority = 20

    def __init__(self):
        # self.database = None
        self.prefix = ""
        self.userinfos = dict()

    def load_data(self, data_path="", redis_pool=None, webqq=""):
        self.prefix = "http://{}/openqq".format(webqq)
        # self.database = redis.StrictRedis(connection_pool=redis_pool)

        return

    def supported_commands(self):
        return ['!smoke']

    def command_received(self, command, content, messageInfo):
        gnumber = messageInfo['group_uid']
        if command == '!roll':
            point = random.randint(0, 100)
            return "{} roll 了 {} 点".format(messageInfo['sender'], point)
        elif command == '!smoke':
            name = content.strip()
            self_uid = messageInfo['sender_uid']
            target_uid = None
            if not name.startswith('@'):
                try:
                    target_uid = int(name)
                except ValueError:
                    return "Illegal QQ"

            else:
                name = name[1:]
                if self.userinfos.get(gnumber) is None:
                    if not self.refresh_group(gnumber):
                        return "No member information currently"
                if self.userinfos[gnumber].get(name) is None:
                    if not self.refresh_group(gnumber):
                        return "No member information currently"
                if self.userinfos[gnumber].get(name) is None:
                    return "Member not found"
                target_uid = self.userinfos[gnumber].get(name)

            success = bool(random.getrandbits(1))
            if success:
                result = self.shutup_group_member(gnumber, target_uid)
            else:
                result = self.shutup_group_member(gnumber, self_uid)
            success_text = "禁言成功" if success else "禁言失败惨遭反噬"
            result_text = "" if result else "\n实际结果:禁言失败"

            return "@{}({}) 试图禁言 {}({}), 成功概率50%\n理论结果:{}{}".format(messageInfo['sender'],
                                                                    messageInfo['sender_uid'], name,
                                                                    target_uid, success_text, result_text)
            # print(content.strip())
            # print(messageInfo)
        return 'received'

    def shutup_group_member(self, group_uid, uid):
        a = requests.get(self.prefix + "/shutup_group_member",
                         params={'group_uid': group_uid, 'member_uid': uid, 'time': 60})
        ret = a.json()
        if ret['status'] == 'success':
            return True
        return False

    def get_name_in_group(self, group_uid, uid):
        a = requests.get(self.prefix + "/search_group", params={'uid': group_uid})
        group_infos = a.json()

    def refresh_group(self, gnumber):
        a = requests.get(self.prefix + "/search_group", params={'uid': gnumber})
        group_infos = a.json()
        try:
            if len(group_infos) > 0:
                users = dict()
                members = group_infos[0]['member']
                for member in members:
                    if member.get('card') is not None:
                        name = member['card']
                    else:
                        name = member['name']
                    if member.get('uid') is None:
                        continue
                    qid = member['uid']
                    users[name] = qid
                self.userinfos[gnumber] = users
                return True
        except KeyError as e:
            print(e)
            print(a.json())
        return False

    def message_received(self, message):
        return ''

    def group_info_changed(self, info):
        print(info)
        return

    def exit(self):
        return
