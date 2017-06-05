import random
from plugin import Plugin


class RollBot(Plugin):
    command_description = "RollBot Usage:\n" \
                          "!roll"
    priority = 20

    def __init__(self):
        return
        # self.database = None
        # self.prefix = ""
        # self.userinfos = dict()

    def weixin_enabled(self):
        return True

    def load_data(self, data_path="", redis_pool=None, **kwargs):
        # self.prefix = "http://{}/openqq".format(webqq)
        # self.database = redis.StrictRedis(connection_pool=redis_pool)

        return

    def supported_commands(self):
        return ['!roll']

    def command_received(self, command, content, messageInfo):
        if command == '!roll':
            point = random.randint(0, 100)
            return "{} roll 了 {} 点".format(messageInfo['sender'], point)
        return 'received'

    def message_received(self, message):
        return ''

    def group_info_changed(self, info):
        print(info)
        return

    def exit(self):
        return
