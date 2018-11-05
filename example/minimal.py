from bothelper import telegrambot
from bothelper import kikbot
from bothelper import facebookbot
from bothelper import htmlbot
from bothelper import discordbot

import bothelper

serv = bothelper.ServerHelper()

class MyMinmalBot(bothelper.Bot):
    startMessageText = """Welcome!"""

    # Builtin event: called if no other function matches
    def onOtherResponse(self, msg):
        self.sendText(msg, "Ok. not sure what to do with it. I don't know this command")

    @serv.textLike("/start")
    def commandStart(self, msg)
        # Show the welcome message
        self.sendText(msg, self.startMessageText)

    @serv.textStartsWith("Hi")
    @serv.textStartsWith("Hey")
    @serv.textStartsWith("Hello")
    def hi(self, msg):
        self.sendText(msg, "Hi :winking_face:")
        self.sendQuestion(msg, "Do you prefer :cat: or  :dog:?", responses=[("Cats", self.showCat), ("Dogs", self.showDog)])

    def showCat(self, msg):
        self.sendText(msg, ":musical_note: Soft kitty, warm kitty, little ball of fur, ...")

    def showDog(self, msg):
        self.sendText(msg, "Who let the dogs out?")

    @serv.textLike("/help")
    @serv.textLike("help")
    @serv.textLike("/about")
    @serv.textLike("about")
    def showHelp(self, msg):
        self.sendText(msg, "This is a minimal BotHelper Example. More at: https://github.com/cvzi/bothelper")


if __name__ == '__main__':
    TITLE = "Minimal Example Bot"
    # HOSTNAME = "https://minimalbot.example.com"
    myBot = MyMinmalBot(serv, TITLE)
    myBot.addFlaskBot(bottype=htmlbot.HtmlBot, route="/")
    # myBot.addFlaskBot(bottype=facebookbot.FacebookBot, route="/facebook", app_secret="123", verify_token="ABC", access_token="XYZ", start_message=myBot.startMessageText)
    # myBot.addFlaskBot(bottype=kikbot.KikBot, route="/kik", name="myminimalkikbotname", apikey="ABC", webhook_host=HOSTNAME)
    # myBot.addFlaskBot(bottype=telegrambot.TelegramBot, route="/telegram", token="XYZ", webhook_host=HOSTNAME)
    # myBot.addBot(bottype=discordbot.DiscordBot, token="AbC.XyZ", prefix="mybot!")
    myBot.run(port=80)  # http://127.0.0.1:80/
