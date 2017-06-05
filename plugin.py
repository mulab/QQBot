class Plugin:
    command_description = "No description"
    priority = 0

    def weixin_enabled(self):
        return False

    def load_data(self, data_path="", redis_pool=None, webqq="127.0.0.1:5000", weixin=None):
        return

    def supported_commands(self):
        return []

    def message_received(self, message):
        return ''

    def command_received(self, command, content, messageInfo):
        return ''

    def exit(self):
        return
