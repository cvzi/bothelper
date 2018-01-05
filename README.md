# bothelper
Small library for kik, Telegram and Facebook Messenger bots

Features:
---------
Supported are Kik, Telegram and Facebook messenger and a chat function on a HTML site (primarily for testing).  
The bots are running on a flask server. The Telegram bot also supports the message loop version without server.  

Currently it can only handle incoming text messages (and locations for Telegram and Facebook) and sending text messages.

Other functions:  

`bothelper.Bot.sendText(msg, text)`  
Send a text message. Supports [emojis by ascii name](https://github.com/carpedm20/emoji#example) and respects the messaging limits of the platforms.

`bothelper.Bot.sendPhoto(msg, url)`  
Send a photo via its url.

`bothelper.Bot.sendQuestion(msg, text, responses, onOtherResponse)`  
Send a text message with predifined reply buttons (a.k.a "quick reply", "InlineKeyboardButton"). 

`bothelper.Bot.user(msg)`  
Store and retrieve data specific to one user, similiar to sessions in PHP.  



Examples:
---------


https://github.com/cvzi/vicibot  


https://github.com/cvzi/chatanonymously  



Minimal example:
----------------

```python
from bothelper import telegrambot
from bothelper import kikbot
from bothelper import facebookbot
from bothelper import htmlbot

import bothelper

serv = bothelper.ServerHelper()

class MyMinmalBot(bothelper.Bot):
    startMessageText = """Welcome!"""
    
    # Builtin event: called if no other function matches
    def onOtherResponse(self, msg):
        self.sendText(msg, "Ok. not sure what to do with it. I don't know this command")
    
    @serv.textLike("/start")
    def commandStart(self, msg):
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
    #HOSTNAME = "https://minimalbot.example.com"
    myBot = MyMinmalBot(serv, TITLE)
    myBot.addFlaskBot(bottype=htmlbot.HtmlBot, route="/")
    #myBot.addFlaskBot(bottype=facebookbot.FacebookBot, route="/facebook", app_secret="123", verify_token="ABC", access_token="XYZ", start_message=myBot.startMessageText)
    #myBot.addFlaskBot(bottype=kikbot.KikBot, route="/kik", name="myminimalkikbotname", apikey="ABC", webhook_host=HOSTNAME)
    #myBot.addFlaskBot(bottype=telegrambot.TelegramBot, route="/telegram", token="XYZ", webhook_host=HOSTNAME)
    
    myBot.run(port=80) # http://127.0.0.1:80/


```

Requirements
------------
 * [Flask](https://pypi.python.org/pypi/Flask)
 * [emoji](https://pypi.python.org/pypi/emoji/0.4.5)
 * [flag](https://github.com/cvzi/flag)
 * [telepot](https://pypi.python.org/pypi/telepot) (only if you want to use the Telegram bot)
 * [kik](https://pypi.python.org/pypi/kik) (only if you want to use the Kik bot)

