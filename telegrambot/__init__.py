
# pip
import telepot
import telepot.loop
import telepot.namedtuple
try:
    import flask # You only need this, if you want to run the webhook variant
except:
    pass
    
class TelegramBot:
    """
    Uses the webhook variant of telepot. Requires a flask server and a public HTTPS address.
    See the telepot documentation for more information:
    `http://telepot.readthedocs.io/en/latest/reference.html#message-loop-and-webhook`_
    """
    
    
    specifications = {
        "maxMessageLength" : 4096
        }
    
    
    
    DISABLEDBUTTON = "<DISABLEDBUTTON>"
    
    def __init__(self, serv, flaskserver, route, token, webhook_host):
        """
        The Telegram webhook relies on security by obscurity. It's important that :param route: 
        is secret and cannot be guessed, because there is no other way to ensure that messages 
        are actually coming from a legit telegram server. 
        The Telegram API documentation suggests that you use your token.
        """
        
        endpoint = "%s.%s@%s" % (self, self.__incoming.__name__, route) # Unique endpoint name
    
        flaskserver.route(route, methods=["GET","POST"], endpoint=endpoint)(self.__incoming)  
        
        self.__webhook_host = webhook_host
        self.__route = route
        
        self._init(serv, token)
        
        
   
    def _init(self, serv, token):
        self.serv = serv
        self.telepotBot = telepot.Bot(token)
        
        self._handle = {
            'chat': self.__handleMessage, 
            'callback_query': self.__handleCallbackQuery
            }
        
        
    def run(self):
        self.__webhook = telepot.loop.OrderedWebhook(self.telepotBot, self._handle)
        self.__webhook.run_as_thread()
        self.telepotBot.setWebhook(self.__webhook_host+self.__route)
               
    def __incoming(self):
    
        self.__webhook.feed(flask.request.data)
        return 'OK'
    
    def userIdFromFrom(self, from_id):
        # return str(from_id)
        return "@t:%d" % from_id
        
    def __handleMessage(self, message):
        content_type, chat_type, chat_id = telepot.glance(message)
        
        message["_bot"] = self
        message["_userId"] = self.userIdFromFrom(message["from"]["id"])
            
        if content_type == "text":
            return self.serv._handleTextMessage(message)
        elif content_type == "location":
            message["_location"] = message["location"]
            return self.serv._handleLocation(message)
            
            
        else:
            raise Exception("Unkown content_type in message: content_type=%s" % str(content_type))
            
    def __handleCallbackQuery(self, callbackquery):
        query_id, from_id, query_data = telepot.glance(callbackquery, flavor='callback_query')
        
        if TelegramBot.DISABLEDBUTTON == query_data:
            return self.telepotBot.answerCallbackQuery(query_id)
        
        msg = {
            "_bot" : self,
            "_userId" : self.userIdFromFrom(from_id),
            "text" : self.serv._demojize(query_data),
            "_orgCallbackQuery" : callbackquery
        }
        
        
        selectedButton = telepot.namedtuple.InlineKeyboardButton(text=self.serv._emojize("%s :white_heavy_check_mark:" % query_data), callback_data=TelegramBot.DISABLEDBUTTON)
        reply_markup = telepot.namedtuple.InlineKeyboardMarkup(inline_keyboard=[[selectedButton]])
        
        self.telepotBot.editMessageReplyMarkup(msg_identifier=(from_id, callbackquery["message"]["message_id"]), reply_markup=reply_markup)
        
        self.serv._handleButtonClick(msg)
            
        return self.telepotBot.answerCallbackQuery(query_id)
            
    def sendText(self, msg, text, buttons=None):
    
        return_id = int(msg["_userId"][3:])
        
        reply_markup = None
        if buttons is not None:
            inlineKeyboardButtons = []
            for button in buttons:
                inlineKeyboardButtons.append(telepot.namedtuple.InlineKeyboardButton(text=self.serv._emojize(button[0]), callback_data=button[1] if isinstance(button[1], str) else button[0]))
            reply_markup = telepot.namedtuple.InlineKeyboardMarkup(inline_keyboard=[inlineKeyboardButtons])
        
        self.telepotBot.sendMessage(return_id, self.serv._emojize(text), reply_markup=reply_markup)

    def sendPhoto(self, msg, url, buttons=None):
    
        return_id = int(msg["_userId"][3:])
        
        reply_markup = None
        if buttons is not None:
            inlineKeyboardButtons = []
            for button in buttons:
                inlineKeyboardButtons.append(telepot.namedtuple.InlineKeyboardButton(text=self.serv._emojize(button[0]), callback_data=button[1] if isinstance(button[1], str) else button[0]))
            reply_markup = telepot.namedtuple.InlineKeyboardMarkup(inline_keyboard=[inlineKeyboardButtons])
        
        self.telepotBot.sendPhoto(return_id, url, reply_markup=reply_markup)




class TelegramBotWithoutFlask(TelegramBot):
    """ 
    Uses the getUpdates() variant of telepot. No server required.
    See the telepot documentation for more information:
    `http://telepot.readthedocs.io/en/latest/reference.html#message-loop-and-webhook`_
    """
    def __init__(self, serv, token):

        self._init(serv, token)

    def run(self):
        self.telepotBot.deleteWebhook()
        telepot.loop.MessageLoop(self.telepotBot, self._handle).run_as_thread()
        
