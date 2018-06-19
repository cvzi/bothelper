#! python3

# builtin
import os
import re
import inspect
import pickle
import threading

# pip
import emoji
import flask

# custom
from . import flag

# debug
from pprint import pprint


class VagueReply:
    class VagueContainer:
        def __init__(self, definitve, vagues):
            self.definitve = definitve
            self.vagues = vagues
            
        def match(self, query):
            for vagueType in self.vagues:
                if vagueType == query:
                    if hasattr(vagueType, 'lastMatch'):
                        return vagueType.lastMatch
                    else:
                        return vagueType
            return None
            
    class TypeRegex:
        def __init__(self, pattern, flags=0):
            self.regex = re.compile(pattern, flags)
            self.lastMatch = None

        def match(self, s):
            m = self.regex.match(s)
            if not m:
                self.lastMatch = None
                return None
            self.lastMatch = m.group(0)
            return self.lastMatch
        
        def __eq__(self, s):
            if isinstance(s, str):
                return self.match(s) is not None
                
            print("%s.__eq__ expected a string" % str(self.__class__.__name__))
            return False
            
    class TypeContainsRegex(TypeRegex):
        def match(self, s):
            self.lastMatch = self.regex.search(s)
            return self.lastMatch
    
     
    def regex(self, pattern, flags=0):
        return VagueReply.TypeRegex(pattern, flags)

    def containsRegex(self, pattern, flags=0):
        return VagueReply.TypeContainsRegex(pattern, flags)

    def string(self, s):
        return s
        
        
    def __init__(self):
        self.data = []
        
        
    def new(self, definitive, vagues=None):
    
        if not vagues:
            vagues = definitive
            definitive = definitive[0]
    
        c = VagueReply.VagueContainer(definitive, vagues)
        self.data.append(c)
        

        return c


class ServerHelper:

    def __init__(self):
        self.commands = {}
        self.bot = None
        
        self.vagueReply = VagueReply()
        
    def _registerBot(self, bot):
        self.bot = bot
        
    def __registerCommand(self, func, condition_wrapper):
        if func.__name__ in self.commands:
            self.commands[func.__name__]["conditions"].append(condition_wrapper)
        else:
            self.commands[func.__name__] = {"conditions": [condition_wrapper], "function": func}
        return func
        
    def _emojize(self, text):
        return flag.flagize(emoji.emojize(text))
        
    def _demojize(self, text):
        return emoji.demojize(flag.dflagize(text))
        
        
    def _sendText(self, msg, text, buttons=None):
        
        # Check length of message
        if "maxMessageLength" in msg["_bot"].specifications and len(text) > msg["_bot"].specifications["maxMessageLength"]:
            N = msg["_bot"].specifications["maxMessageLength"]
            
            re_newline = re.compile(r"\n|$", flags=re.MULTILINE)
            re_whitespace = re.compile("\s+", flags=re.MULTILINE)
            re_wordend = re.compile("\b\s*", flags=re.MULTILINE)
            
            # Split long message up
            while len(text) > N:
                # Try to split at newline
                m = re_newline.search(text, pos=N-50)
                if not m: # try to split at whitespace
                    m = re_whitespace.search(text, pos=N-50)
                    if not m: # try to split at wordend
                        m = re_wordend.search(text, pos=N-50)
                    
                if not m or m.end() == len(text):
                    # split anywhere
                    text, rest = text[0:N-5] + "...", "..." + text[N-5:].strip()
                else:
                    # split at match
                    text, rest = text[0:m.start()], text[m.end():].strip()
                
                if len(rest) == 0:
                    text = rest
                    break
                else:
                    msg["_bot"].sendText(msg, text)
                
                text = rest
        
        return msg["_bot"].sendText(msg, text, buttons)
            
    def _sendLink(self, msg, url, buttons=None, text=""):
        return msg["_bot"].sendLink(msg, url, buttons, text)
            
    def _sendPhoto(self, msg, url, buttons=None):
    
        return msg["_bot"].sendPhoto(msg, url, buttons)
           

    def _handleTextMessage(self, msg):
        user = self.bot.user(msg)
        
        
        msg["text_nice"] = self._demojize(msg["text"].strip())
        msg["text_nice_lower"] = msg["text_nice"].lower()
        
        # Match a vague answer
        m = user.getResponse(msg["text_nice_lower"])
        if m is not None:
            function = m[0]
            
            function(msg)
            
            return True
        
        # Fallback to question onOtherResponse
        onOtherResponse = user.getOnOtherResponse()
        if onOtherResponse is not None:
            function, lastStage = onOtherResponse[1]
            
            if len(inspect.signature(function).parameters) == 2:
                function(msg, lastStage)
            else:
                function(msg)
            return True
    
    
        # Match any other
        for commandName in self.commands:
            for condition in self.commands[commandName]["conditions"]:
                if condition(msg):
                    self.commands[commandName]["function"](self.bot, msg)
                    return True
                    
        # Fallback to generic onOther
        if hasattr(self.bot, 'onOtherResponse'):
            self.bot.onOtherResponse(msg)
            return True
        
        print("No handler found for text message: %s" % msg["text_nice"].encode('unicode-escape').decode('ascii'))
        return False
        
        
    def _handleFriendPicker(self, msg):
        if hasattr(self.bot, 'onFriendPicker'):
            self.bot.onFriendPicker(msg)
            return True
        return False
        
        
    def _handleLocation(self, msg):
        if hasattr(self.bot, 'onLocation'):
            self.bot.onLocation(msg)
            return True
        return False
    
        
    def _handleButtonClick(self, msg):
        user = self.bot.user(msg)
        
        
        button = user.getButton(msg["text"])
        
        if button is None:
            return self._handleTextMessage(msg)
 
        if isinstance(button[1], str):
            msg["text"] = button[1]
            msg["text_nice"] = self._demojize(msg["text"].strip())
            msg["text_nice_lower"] = msg["text_nice"].lower()
             
            return self._handleTextMessage(msg)
        
        else:
            msg["text_nice"] = self._demojize(msg["text"].strip())
            msg["text_nice_lower"] = msg["text_nice"].lower()
            
            function = button[1]
            
            function(msg)
        
        return True


    def all(self, *args):
        def wrapper(func):
            org_func_name = func.__name__
            func.__name__ = "fake_"+org_func_name
            
            for arg in args:
                arg(func)

            conditions = self.commands.pop(func.__name__)["conditions"]
            func.__name__ = org_func_name

            def __condition(self, msg):
                return all([condition(msg) for condition in conditions])
            
            def condition_wrapper(msg):
                return __condition(self, msg)

            return self.__registerCommand(func, condition_wrapper)
        
        return wrapper
        
        

    def textLike(self, text):
        def __condition(self, msg):
            return text.strip().lower() == msg["text_nice_lower"]
        
        def condition_wrapper(msg):
            return __condition(self, msg)
        def register_command(func):
            return self.__registerCommand(func, condition_wrapper)
        
        
        return register_command
        
    def textStartsWith(self, text):
        def __condition(self, msg):
            return msg["text_nice_lower"].startswith(text.strip().lower())
        
        def condition_wrapper(msg):
            return __condition(self, msg)
        def register_command(func):
            return self.__registerCommand(func, condition_wrapper)
        
        
        return register_command
        
    def textRegexMatch(self, rawpattern, flags=re.IGNORECASE):
        regex_pattern = re.compile(rawpattern, flags)
        
        def __condition(self, msg):
            return regex_pattern.match(msg["text_nice"])
        
        def condition_wrapper(msg):
            return __condition(self, msg)
        def register_command(func):
            return self.__registerCommand(func, condition_wrapper)
        
        
        return register_command
    
    def userIdEquals(self, userId):
        def __condition(self, msg):
            return userId == msg["_userId"]
        
        def condition_wrapper(msg):
            return __condition(self, msg)
        def register_command(func):
            return self.__registerCommand(func, condition_wrapper)
            
        return register_command
    

        

    
class Bot:

    def __init__(self, serverHelper, title="Bot", userFile=None):
        self.serv = serverHelper
        self.serv._registerBot(self)
        self.title = title
        self.__flaskServer = None
        self.telegramBot = None
        self.kikBot = None
        self.facebookBot = None
        
        self.bots = []
        
        self.users = {}
        self.userFile = userFile
        self.userStorage = None
        
        if self.userFile is not None and os.path.isfile(self.userFile):
        
            with open(self.userFile, "rb") as fs:
            
                self.users = pickle.load(fs)
                
                
    def addPermanentStorage(self, storage):
        self.userStorage = storage
        
    def getPermanentStorage(self):
        return self.userStorage
        
    def getBotByName(self, name):
        for bot in self.bots:
            if type(bot).__name__ == name:
                return bot
        
    def getFlask(self):
        if self.__flaskServer is None:
            self.__flaskServer = flask.Flask(__name__)
        
        return self.__flaskServer
        
             
    def __runFlask(self, host, port):
        return self.__flaskServer.run(port=port, host=host, debug=False, threaded=True)
        
    def addBot(self, bottype, *args, **kwargs):
        bot = bottype(self.serv, *args, **kwargs)
        self.bots.append(bot)
        print("Added %s" % str(bot))
        return bot
    
    def addFlaskBot(self, bottype, *args, **kwargs):
        bot = bottype(self.serv, self.getFlask(), *args, **kwargs)    
        self.bots.append(bot)
        print("Added %s" % str(bot))
        return bot

    
    def run(self, runFlask=True, host='127.0.0.1', port=8080):   
        """Starts all bots.
        If runFlask is True, it will run Flask's server on standard host/port. 
        This call will block the current thread forever. 
        If False, it will just return the Flask and you may run it later.
        You should not use Flask's server for production/deployment"""
        
        print("Starting "+self.title+"...")
        for bot in self.bots:
            if hasattr(bot, "run"):
                bot.run()
            
        if self.__flaskServer is not None:
            if runFlask:
                print("Starting Flask...")
                return self.__runFlask(host, port)

        return self.__flaskServer
        
    def user(self, msg):
        userId = msg["_userId"]
        if not userId in self.users:
            self.users[userId] = User(userId=userId, lastMsg=msg, storage=self.userStorage, bot=msg["_bot"])
        
        self.users[userId].msg(msg)
        return self.users[userId]
        
    def startConversation(self, msg, forceExitCommand="/cancel"):
        user = self.user(msg)
        user.startConversation(forceExitCommand)
        
    def endConversation(self, msg):
        self.user(msg).endConversation()

    def createEmptyMessage(self, fromMsg, toUserId):
        return {
            "_bot" : fromMsg["_bot"],
            "_responseMessages" : [],
            "_responseSent" : True,
            "_userId" : toUserId
        }
        
    def sendText(self, msg, text, buttons=None):
        if isinstance(msg, User):
            msg = msg.msg()
        return self.serv._sendText(msg, text, buttons)
        
    def sendLink(self, msg, url, buttons=None, text=""):
        if isinstance(msg, User):
            msg = msg.msg()
        return self.serv._sendLink(msg, url, buttons, text)
        
        
    def sendPhoto(self, msg, url, buttons=None):
        if isinstance(msg, User):
            msg = msg.msg()
        return self.serv._sendPhoto(msg, url, buttons)
        
        
    def sendQuestion(self, msg, text, responses=None, onOtherResponse=None, onOtherResponseReturn=None):
        if isinstance(msg, User):
            msg = msg.msg()
        user = self.user(msg)
        
        if responses is None:
            responses = []
        
        user.rememberResponses(responses, onOtherResponse, onOtherResponseReturn)
    
        return self.serv._sendText(msg, text, buttons=responses)
    
    def sendTextWithButtons(self, msg, text, buttons):
        if isinstance(msg, User):
            msg = msg.msg()
        return self.serv._sendText(msg, text, buttons=buttons)
        
        
    def saveUserFile(self):
        if self.userFile is not None:
            with open(self.userFile, "wb") as fs:
                pickle.dump(self.users, fs)
                
                
    def runInThread(self, fun, *args, **kwargs):
        try:
            import asyncio
        except ModuleNotFoundError:
            pass
        
        def runIt(loop, *args, **kwargs):
            if loop:
                asyncio.set_event_loop(loop)
            fun(*args, **kwargs)
        
        try:
            loop = asyncio.get_event_loop()
        except (RuntimeError, NameError):
            loop = None
        t = threading.Thread(target=runIt, args=(loop, *args), kwargs=kwargs)
        t.daemon = True
        t.start()





class User:

    def __init__(self, userId, lastMsg=None, storage=None, bot=None):
        self.__lastMsg = lastMsg
        self.userId = userId
        self.bot = bot
        self.storage = storage
        self.data = {}
        self.userdata = {}
        if self.storage is not None:
            self.userdata = self.storage.retrieve(self.bot, userId)
        self.conversation = None
        self.onOtherResponseNAME = "__onOtherResponse__123"
        
    def msg(self, msg=None):
        if msg is None:
            return self.__lastMsg
        
        self.__lastMsg = msg
        return msg

    def startConversation(self, forceExitCommand):
        self.conversation = {}
        
    def endConversation(self):
        self.conversation = None
        
    def __clearResponses(self):
        root = self.data if self.conversation is None else self.conversation
        
        root["buttons"] = {}
        
    def clearResponses(self):
        root = self.data if self.conversation is None else self.conversation
        
        root["buttons"] = {}
        
        
    def storeValue(self, key, value):
        self.userdata[key] = value
        if self.storage is not None:
            self.storage.store(self.bot, self.userId, key, value)
        
    def retrieveValue(self, key, default=None):
        if key in self.userdata:
            return self.userdata[key]
        else:
            return default
        
    def clearValues(self):
        self.userdata = {}
        if self.storage is not None:
            self.storage.clear(self.bot, self.userId)
        
    def rememeberOnOtherResponse(self, onOtherResponse, onOtherResponseReturn=None):
        self.rememberResponse((self.onOtherResponseNAME, (onOtherResponse, onOtherResponseReturn)))
        
    def rememberResponse(self, button):
        root = self.data if self.conversation is None else self.conversation
        
        if not "buttons" in root:
            root["buttons"] = {}
        root["buttons"][button[0]] = button
        
    def rememberResponses(self, buttons, onOtherResponse=None, onOtherResponseReturn=None):
        root = self.data if self.conversation is None else self.conversation
        
        if not "buttons" in root:
            root["buttons"] = {}
        for button in buttons:
            root["buttons"][button[0]] = button
            
        if onOtherResponse is not None:
            self.rememeberOnOtherResponse(onOtherResponse, onOtherResponseReturn)
            
            
    def getButton(self, key, clear=True):
        root = self.data if self.conversation is None else self.conversation
        
        if not "buttons" in root:
            return None
        
        if not key in root["buttons"]:
            oldkey = key
            for b in root["buttons"]:
                if len(root["buttons"][b]) > 1 and root["buttons"][b][1] == key:
                    key = b
                    break
                
            if oldkey == key:
                return None
        
        ret = root["buttons"][key]
        
        if clear:
            self.__clearResponses()
        
        return ret
        
    def getOnOtherResponse(self):
        return self.getButton(self.onOtherResponseNAME, clear=False)
        
    def getResponse(self, query, clear=True):
        root = self.data if self.conversation is None else self.conversation
        
        if not "buttons" in root:
            return None
            
        query = query.lower()
        
        def check():
            for key, button in root["buttons"].items():
                if button[0].lower() == query: #compare strings
                    return button[1], button[0], button[0].lower()
                if len(button) > 2:
                
                    if not isinstance(button[2], list):
                        vagueContainers = [ button[2] ]
                    else:
                        vagueContainers = button[2]
                        
                    for vagueContainer in vagueContainers:
                        if isinstance(vagueContainer, VagueReply.VagueContainer):
                            m = vagueContainer.match(query)
                            if m is not None:
                                return button[1], vagueContainer.definitve, m

            return None
            
        
        ret = check()
        if ret is None:
            return None
        
        if clear:
            self.__clearResponses()
        
        return ret
        

        
