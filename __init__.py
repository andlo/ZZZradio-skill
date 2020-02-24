from mycroft import MycroftSkill, intent_file_handler


class Radio(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('radio.intent')
    def handle_radio(self, message):
        self.speak_dialog('radio')


def create_skill():
    return Radio()

