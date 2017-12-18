
# pip
import flask 
import kik
import kik.messages


class KikBot:
  
    def __init__(self, serv, flaskserver, route, name, apikey, webhook_host):
        """
        It is suggested to use a secret :param route: to ensure that nobody can send malicious requests.
        """
        endpoint = "%s.%s@%s" % (self, self.__incoming.__name__, route) # Unique endpoint name
        
        flaskserver.route(route, methods=["POST"], endpoint=endpoint)(self.__incoming)  
        
        self.serv = serv
        
        self.kik_api = kik.KikApi(name, apikey)
        self.kik_api.set_configuration(kik.Configuration(webhook=webhook_host+route))
         

    def __incoming(self):
        """
        Handle incoming messages to the bot. All requests are authenticated using the signature in
        the 'X-Kik-Signature' header.
        :return: flask.Response
        """
        # verify that this is a valid request
        if not self.kik_api.verify_signature(
                flask.request.headers.get("X-Kik-Signature"), flask.request.get_data()):
            return "Verification token mismatch", 403

        messages = flask.request.json["messages"]

        response_messages = []

        for message in messages:
        
            ret = self.__handleMessage(message)
            
            if isinstance(ret, kik.messages.TextMessage):
                response_messages.append(ret)
            elif isinstance(ret, list):
                response_messages.extend(ret)

        self.__sendMessages(response_messages)

        return "Ok", 200
        
    def __sendMessages(self, response_messages):
        if response_messages:
            self.kik_api.send_messages(response_messages)
        
    def __handleMessage(self, message):
        message["_bot"] = self
        message["_userId"] = message["from"]
        message["_responseMessages"] = []
        message["_responseSent"] = False
        
        
        if "metadata" in message and "_type" in message["metadata"]:
            if message["metadata"]["_type"] == "SuggestedTextResponse":
                message["text"] = message["metadata"]["_button"]
                self.serv._handleButtonClick(message)
            else:
                raise Exception("Unkown _type in metadata: _type=%s" % str(message["metadata"]["_type"]))
        
        
        elif message["type"] == "start-chatting":
            if not "body" in message:
                message["text"] = "/start"
            else:
                message["text"] = message["body"]
            self.serv._handleTextMessage(message)
        
        
        elif message["type"] == "text":
            message["text"] = message["body"]
            self.serv._handleTextMessage(message)
            
        else:
            raise Exception("Unkown type in message: type=%s" % str(message["type"]))
         
        message["_responseSent"] = True
        return message["_responseMessages"]
            
    def sendText(self, msg, text, buttons=None):
        keyboards = None
        if buttons is not None:
            responses = []
            for button in buttons:
                response = kik.messages.TextResponse(self.serv._emojize(button[0]))
                response.metadata = {"_type": "SuggestedTextResponse", "_button" : button[1] if isinstance(button[1], str) else button[0]}
                responses.append(response)
            keyboards = [kik.messages.SuggestedResponseKeyboard(responses=responses)]
    
        msg["_responseMessages"].append(kik.messages.TextMessage(
            to=msg["_userId"],
            chat_id=msg["chatId"],
            body=self.serv._emojize(text),
            keyboards=keyboards
            )
        )
        
        if msg["_responseSent"]:
            # The original message was already sent back, so we need send the reply seperately
            self.__sendMessages(msg["_responseMessages"])
        
     
    def sendPhoto(self, msg, url, buttons=None):
        keyboards = None
        if buttons is not None:
            responses = []
            for button in buttons:
                response = kik.messages.TextResponse(self.serv._emojize(button[0]))
                response.metadata = {"_type": "SuggestedTextResponse", "_button" : button[1] if isinstance(button[1], str) else button[0]}
                responses.append(response)
            keyboards = [kik.messages.SuggestedResponseKeyboard(responses=responses)]
    
        msg["_responseMessages"].append(kik.messages.PictureMessage(
            to=msg["_userId"],
            chat_id=msg["chatId"],
            pic_url=url,
            keyboards=keyboards
            )
        )
        
        if msg["_responseSent"]:
            # The original message was already sent back, so we need send the reply seperately
            self.__sendMessages(msg["_responseMessages"])
    