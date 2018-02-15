import json
import hmac
import hashlib

# pip
import requests
import flask




API_URL = "https://graph.facebook.com/v2.6/me/"

class FacebookBot:
    """
    Based on `https://github.com/hartleybrody/fb-messenger-bot/blob/master/app.py`_
    """
  
  
    specifications = {
        "maxMessageLength" : 2000
        }

  
    def __init__(self, serv, flaskserver, route, app_secret, verify_token, access_token, start_message=None):
        """
        It is suggested to use a secret :param route: to ensure that nobody can send malicious 
        requests.
        """
    
        self.serv = serv
        self.app_secret = app_secret
        self.verify_token = verify_token
        self.access_token = access_token
        
        endpointGet = "%s.%s@%s" % (self, self.__onGet.__name__, route) # Unique endpoint name
        endpointPost = "%s.%s@%s" % (self, self.__onPost.__name__, route) # Unique endpoint name  
        
        flaskserver.route(route, methods=['GET'], endpoint=endpointGet)(self.__onGet)
        flaskserver.route(route, methods=['POST'], endpoint=endpointPost)(self.__onPost)  
        
        if start_message is not None:
            self.setStartMessage(start_message)
            
    def __send(self, data, section="messages"):
                
        params = {
            "access_token": self.access_token
        }
        headers = {
            "Content-Type": "application/json"
        }

        r = requests.post(API_URL + section, params=params, headers=headers, data=json.dumps(data))
        if r.status_code != 200:
            print("FacebookBot.__send: %s returned %d" % (API_URL, r.status_code))
        
        return r
            

    def __onGet(self): 
        """
        Handle the initial verification of your webhook. This should only be called once when 
        you setup your webhook.
        :return: flask.Response
        """
        if flask.request.args.get("hub.mode") == "subscribe" and flask.request.args.get("hub.challenge"):
            if not flask.request.args.get("hub.verify_token") == self.verify_token:
                return "Verification token mismatch", 403
            return flask.request.args["hub.challenge"], 200

        return "Missing hub.* parameter", 400
        
        
    def __validateRequest(self):
        """
        Verifies that a request body correctly matches the value in the X-Hub-Signature header.
        See `https://developers.facebook.com/docs/messenger-platform/webhook-reference#security`_.
        """
        signature = "sha1=" + hmac.new(key=self.app_secret.encode("utf-8"), msg=flask.request.get_data(), digestmod=hashlib.sha1).hexdigest()
        
        if flask.request.headers["X-Hub-Signature"] != signature:
            return False

        return True

    def __onPost(self):
        """
        Handle incoming messages to the bot. All requests are authenticated using the signature in
        the 'X-Kik-Signature' header.
        :return: flask.Response
        """
        # endpoint for processing incoming messaging events
        
        try:
            if not self.__validateRequest():
                print("__onPost: Validation failed!")
                return "Signature mismatch",403
            data = flask.request.get_json()
            assert data != None
        except:
            return "Corrupt json data", 400
        
        #print(str(data).encode("unicode-escape"))  # Good for testing

        
        if data and "object" in data and data["object"] == "page":

            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:

                    if messaging_event.get("message"):  # someone sent us a message

                        self.__handleMessage(messaging_event)

                    if messaging_event.get("delivery"):  # delivery confirmation
                        pass

                    if messaging_event.get("optin"):  # optin confirmation
                        pass

                    if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                        pass
        else:
            print("__onPost: No data")
                        
                        

        return "Ok", 200


 
    def __handleMessage(self, messaging_event):
        messaging_event["_bot"] = self
        messaging_event["_userId"] = messaging_event["sender"]["id"] 
        
        #print(str(messaging_event).encode("unicode-escape"))  # Good for testing
        
        if "attachments" in messaging_event["message"]:
            for attachment in messaging_event["message"]["attachments"]:
                if attachment["type"] == "location":
                    messaging_event["_location"] = {
                        "latitude": attachment["payload"]["coordinates"]["lat"],
                        "longitude": attachment["payload"]["coordinates"]["long"]
                    }
                    self.serv._handleLocation(messaging_event)
    
        if "quick_reply" in messaging_event["message"]:
            messaging_event["text"] = messaging_event["message"]["quick_reply"]["payload"]
            return self.serv._handleButtonClick(messaging_event)  
        elif "text" in messaging_event["message"]:
            messaging_event["text"] = messaging_event["message"]["text"]
            return self.serv._handleTextMessage(messaging_event)  
        

    def __sendMessage(self, recipient_id, message, buttons):
        data = {
            "messaging_type" : "RESPONSE",
            "recipient": {
                "id": recipient_id
            },
            "message": message
        }
        
        if buttons is not None and len(buttons) > 0:
            # Quick-reply documentation: https://developers.facebook.com/docs/messenger-platform/send-api-reference/quick-replies
            quick_replies = []
            for button in buttons:
            
                title = self.serv._emojize(button[0])
                if len(title) > 20:
                    print("FacebookBot.__sendMessage: Quick-reply/button title has a 20 character limit")
                    
                
                quick_replies.append({
                    "content_type" : "text",
                    "title" : title[0:20],
                    "payload" : button[1] if isinstance(button[1], str) else button[0]
                  })
            data["message"]["quick_replies"] = quick_replies
        
        r = self.__send(data)
        
        ret = json.loads(r.text)
        
        if "error" in ret:
            print("Could not send message:\n%s" % (r.text.encode('unicode-escape').decode('ascii')))
        
    
    def sendText(self, msg, text, buttons=None):
        
        return self.__sendMessage(msg["_userId"], {
            "text" : self.serv._emojize(text)
        }, buttons)
    
    def sendLink(self, msg, url, buttons=None):
        try:
            domain = url.split("//" , 1)[1]
            if domain.startswith("www."):
                domain = domain[4:]
            if "/" in domain:
                domain = domain.split("/", 1)[0]
             
            domain = domain[0:15]
            button_text = "Open %s" % domain
        except:
            button_text = "Open website"
        
        # Ref.: https://developers.facebook.com/docs/messenger-platform/reference/buttons/url
        return self.__sendMessage(msg["_userId"], {
            "attachment" : {
                "type" : "template",
                "payload" : {   
                    "template_type": "button",
                    "text": url,
                    "buttons": [
                      {
                        "type":"web_url",
                        "url": url,
                        "title": button_text, # Button title. 20 character limit.
                        "messenger_extensions": "false"
                      }
                    ]
                }
            }
        }, buttons)

    
    def sendPhoto(self, msg, url, buttons=None):
        
        return self.__sendMessage(msg["_userId"], {
            "attachment" : {
                "type" : "image",
                "payload" : {   
                    "url" : url
                }
            }
        }, buttons)
 
        
        

    def setStartMessage(self, greeting):
        """
        Set the Greeting Text as defined in
        `https://developers.facebook.com/docs/messenger-platform/messenger-profile/greeting-text`_
        """
        data = {}
    
        if isinstance(greeting, str):
            data["greeting"] = [{
                "locale" : "default",
                "text" : greeting }]
            
        else:
            data["greeting"] = greeting
            
        r = self.__send(data, section="messenger_profile")
        
        ret = json.loads(r.text)
        
        assert ret["result"] == "success"
        


        