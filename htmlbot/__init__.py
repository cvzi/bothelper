import json
import random
import os

# pip
import flask


class HtmlBot:

    specifications = {
        "maxMessageLength" : 10000
        }
        
    def __init__(self, serv, flaskserver, route):
    
        self.serv = serv
        
        endpointGet = "%s.%s@%s" % (self, self.__onGet.__name__, route) # Unique endpoint name
        endpointPost = "%s.%s@%s" % (self, self.__onPost.__name__, route) # Unique endpoint name
        
        flaskserver.route(route, methods=['GET'], endpoint=endpointGet)(self.__onGet)
        flaskserver.route(route, methods=['POST'], endpoint=endpointPost)(self.__onPost)
        
        
        self.users = {}
        self.replies_queue = {}
        
        with open(os.path.join(os.path.dirname(__file__), "chat.html")) as fs:
            self.html = fs.read()
        
        
    
    def __onGet(self):
        # Send the HTML page
        return self.html, 200


    def __onPost(self):
        # endpoint for processing incoming messaging events
        
        try:
            data = flask.request.get_json()
            assert data != None
        except:
            return "Corrupt json data", 400
        
        print(str(data).encode("unicode-escape"))

        
        # validate
        if "init" in data:
            uid = str(random.randint(0,100))
            while uid in self.users:
                uid = str(random.randint(0,1000000))
            self.users[uid] = data["init"]
            data["uid"] = uid
        else:
            if data["uid"] in self.users and self.users[data["uid"]] != data["secret"]:
                return '{"error" : "secret mismatch"}', 403
            uid = data["uid"]
       
        
        if "text" in data:
            return json.dumps({"uid":uid,"replies":self.__handleMessage(data)}), 200
        else:
            return json.dumps({"uid":uid,"replies":self.__popQueuedReplies(data)}), 200
            
            
        return "Ok", 200



    def __handleMessage(self, msg):
        msg["_bot"] = self
        msg["_userId"] = msg["uid"] 
        msg["_responseMessages"] = []
        msg["_responseSent"] = False
                
        if "quick_reply" in msg:
            self.serv._handleButtonClick(msg)
            
        elif "text" in msg:
            self.serv._handleTextMessage(msg)

        msg["_responseSent"] = True
        return msg["_responseMessages"]
        
    def __popQueuedReplies(self, msg):
        uid = msg["uid"]
        
        if not uid in self.replies_queue:
            return []
        
        
        replies = self.replies_queue[uid]
        self.replies_queue[uid] = []
        return replies
    
        
    def __sendToQueue(self, msg, text, formattedbuttons):
        # queue the reply for the next polling event
        uid = msg["_userId"]
        
        reply = {
            "to" : msg["_userId"],
            "text" : self.serv._emojize(text),
            "buttons" : formattedbuttons
            }
        
        
        if not uid in self.replies_queue:
            self.replies_queue[uid] = [reply]
        else:
            self.replies_queue[uid].append(reply)
        
        
    def sendText(self, msg, text, buttons=None):
        b = None
        if buttons:
            b = [(button[0], button[1] if isinstance(button[1], str) else button[0]) for button in buttons]
            
    
        if msg["_responseSent"]:
            # The original message was already sent back, so we need to queue the reply for the next polling event
            self.__sendToQueue(msg, text, b)
        else:
            msg["_responseMessages"].append({
                "to" : msg["_userId"],
                "text" : self.serv._emojize(text),
                "buttons" : b
                }
            )
    
    def sendPhoto(self, msg, url, buttons=None):
        b = None
        if buttons:
            b = [(button[0], button[1] if isinstance(button[1], str) else button[0]) for button in buttons]
            
    
        msg["_responseMessages"].append({
            "to" : msg["_userId"],
            "text" : '<img src="'+url+'">',
            "buttons" : b
            }
        )
        
    def sendLink(self, msg, url, buttons=None):
        b = None
        if buttons:
            b = [(button[0], button[1] if isinstance(button[1], str) else button[0]) for button in buttons]
            
    
        msg["_responseMessages"].append({
            "to" : msg["_userId"],
            "text" : '<a href="'+url+'">'+url.split("://", 1)[1]+'</a>',
            "buttons" : b
            }
        )
        
        