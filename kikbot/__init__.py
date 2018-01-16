
# pip
import flask 
import kik
import kik.messages

import threading
import time


class KikBot:


    specifications = {
        "maxMessageLength" : 1000, # TODO Just a guess. What's the real limit? 
        "maxMessagesPerUser" : 5, # https://dev.kik.com/#/docs/messaging#sending-messages
        "maxMessagesPerBatch" : 25, # https://dev.kik.com/#/docs/messaging#rate-limits
        "waitBetweenBatches" : 2
        }
        
        
        
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
        
    def __sendMessages(self, response_messages, wait=0):
        if wait:
            time.sleep(wait)
    
        if response_messages:
            if len(response_messages) > self.specifications["maxMessagesPerUser"]:
                remaining = response_messages
                while len(remaining) > 0:
                    # Respect limits: https://dev.kik.com/#/docs/messaging#sending-messages and https://dev.kik.com/#/docs/messaging#rate-limits
                    current_batch = [] # Collect messages to send now, respecting both limits
                    next_batch = [] # These messages should be sent in next batch, before the remaining message
                    to_users = {} # Count messages per user in batch
                    i = 0 # Count total messages in batch
                    N = self.specifications["maxMessagesPerBatch"] # Max messages per Batch
                    for message in remaining[0:N]:
                        if not message.to in to_users:
                            to_users[message.to] = 0
                        
                        if to_users[message.to] < self.specifications["maxMessagesPerUser"] and i < N:
                            # Ok
                            current_batch.append(message)
                        elif i < N:
                            # user has enough messages in this batch
                            next_batch.append(message)
                        else:
                            # batch is full with messages. 
                            next_batch.append(message)
                        
                        to_users[message.to] += 1
                        i += 1
                    
                    if current_batch:
                        # Send batch
                        self.kik_api.send_messages(current_batch)
                    
                    remaining = next_batch + remaining[N:]
                    
                    if current_batch and remaining:
                        # Wait before sending the next batch
                        time.sleep(specifications["waitBetweenBatches"])
            
            else:
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
        
        if len(message["_responseMessages"]) > self.specifications["maxMessagesPerUser"]:
            
            batch, remaining = message["_responseMessages"][0 : self.specifications["maxMessagesPerUser"] ] , message["_responseMessages"][self.specifications["maxMessagesPerUser"] : ]
            
            t = threading.Thread(target=self.kik_api.send_messages, args=(remaining, 5))
            t.daemon = True
            t.start()
            
            return batch
        
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
            # The original message was already sent back, so we need to send the reply seperately
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
    