
# pip
import flask 
import kik
import kik.messages

import threading
import time

from pprint import pprint

class KikBot:


    specifications = {
        "maxMessageLength" : 1000, # TODO Just a guess. What's the real limit? 
        "maxMessagesPerUser" : 5, # https://dev.kik.com/#/docs/messaging#sending-messages
        "maxMessagesPerBatch" : 25, # https://dev.kik.com/#/docs/messaging#rate-limits
        "maxBroadcastsPerBatch" : 100, # https://dev.kik.com/#/docs/messaging#rate-limits
        "waitBetweenBatches" : 2,
        "restrictedChars" : {
            "\x84" : "\"",
            }
        
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
         
    def _sanitize(self, text):
        for key in self.specifications["restrictedChars"]:
            text = text.replace(key, self.specifications["restrictedChars"][key])
        return text

    def __incoming(self):
        """
        Handle incoming messages to the bot. All requests are authenticated using the signature in
        the 'X-Kik-Signature' header.
        :return: flask.Response
        """
        # verify that this is a valid request
        # TODO verify timestamp as suggested at: https://dev.kik.com/#/docs/messaging#api-authentication-with-webhook
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
        if not response_messages:
            return
        
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
                    self.__sendMessages(current_batch)
                
                remaining = next_batch + remaining[N:]
                
                if current_batch and remaining:
                    # Wait before sending the next batch
                    time.sleep(specifications["waitBetweenBatches"])
                
        else:
            self.kik_api.send_messages(response_messages)
        
        
    def __sendBroadcasts(self, response_messages):
        if not response_messages:
            return
        
        if len(response_messages) > self.specifications["maxMessagesPerUser"]:
            remaining = response_messages
            while len(remaining) > 0:
                # Respect limits: https://dev.kik.com/#/docs/messaging#sending-messages and https://dev.kik.com/#/docs/messaging#rate-limits
                current_batch = [] # Collect messages to send now, respecting both limits
                next_batch = [] # These messages should be sent in next batch, before the remaining message
                to_users = {} # Count messages per user in batch
                i = 0 # Count total messages in batch
                N = self.specifications["maxBroadcastsPerBatch"] # Max messages per Batch
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
                    self.__sendBroadcasts(current_batch)
                
                remaining = next_batch + remaining[N:]
                
                if current_batch and remaining:
                    # Wait before sending the next batch
                    time.sleep(specifications["waitBetweenBatches"])
                
        else:
            self.kik_api.send_broadcast(response_messages)
        
        
        
        
        
    
    def __handleMessage(self, message):
        message["_bot"] = self
        message["_userId"] = message["from"]
        message["_responseMessages"] = []
        message["_responseSent"] = False
        
        if "type" in message  and message["type"] != "text":
            pprint(message)
        
        if "metadata" in message and message["metadata"] and "_type" in message["metadata"]:
            if message["metadata"]["_type"] == "SuggestedTextResponse":
                message["text"] = message["metadata"]["_button"]
                self.serv._handleButtonClick(message)
            elif message["metadata"]["_type"] == "FriendPickerResponse":
                message["text"] = message["metadata"]["_button"]
                self.serv._handleFriendPicker(message)
            else:
                raise Exception("Unkown _type in metadata: _type=%s" % str(message["metadata"]["_type"]))
        
        
        elif message["type"] == "start-chatting":
            if "body" in message and message["body"]:
                message["text"] = message["body"]
            else:
                message["text"] = "/start"
            self.serv._handleTextMessage(message)
        
        elif message["type"] == "scan-data":
            if "data" in message and message["data"]:
                message["text"] = message["data"]
            else:
                message["text"] = "/start"
            self.serv._handleTextMessage(message)
        
        elif message["type"] == "friend-picker":
            if "metadata" in message:
                message["text"] = message["metadata"]
            else:
                message["text"] = None
            self.serv._handleFriendPicker(message)
        
        elif message["type"] == "text":
            message["text"] = message["body"]
            self.serv._handleTextMessage(message)
            
        else:
            # Other type
            if "body" in "text" and message["body"]:
                message["text"] = message["body"]
            else:
                message["text"] = message["type"]
                
            self.serv._handleTextMessage(message)
        
            print("Unkown type in message: type=%s" % str(message["type"]))
         
        message["_responseSent"] = True
        
        if len(message["_responseMessages"]) > self.specifications["maxMessagesPerUser"]:
            
            batch, remaining = message["_responseMessages"][0 : self.specifications["maxMessagesPerUser"] ] , message["_responseMessages"][self.specifications["maxMessagesPerUser"] : ]
            
            t = threading.Thread(target=self.kik_api.send_messages, args=(remaining, 5))
            t.daemon = True
            t.start()
            
            return batch
        
        return message["_responseMessages"]
    
    
    def _formatButtons(self, buttons):
        keyboards = None
        if buttons is not None:
            responses = []
            for button in buttons:
                if button[1] == "friend-picker":
                    response = kik.messages.FriendPickerResponse(self.serv._emojize(button[0]))
                    response.metadata = {"_type": "FriendPickerResponse", "_button" : button[1]}
                    responses.append(response)
                else:
                    response = kik.messages.TextResponse(self.serv._emojize(button[0]))
                    response.metadata = {"_type": "SuggestedTextResponse", "_button" : button[1] if isinstance(button[1], str) else button[0]}
                    responses.append(response)
            keyboards = [kik.messages.SuggestedResponseKeyboard(responses=responses)]
        return keyboards
    
    
    def sendText(self, msg, text, buttons=None):
        keyboards = self._formatButtons(buttons)
    
        if not "_responseMessages" in msg:
            msg["_responseMessages"] = []
    
        msg["_responseMessages"].append(kik.messages.TextMessage(
            to=msg["_userId"],
            chat_id=msg["chatId"] if "chatId" in msg else None,
            body=self._sanitize(self.serv._emojize(text)),
            keyboards=keyboards
            )
        )
        
        if msg["_responseSent"]:
            # The original message was already sent back, so we need to send the reply separately
            self.__sendMessages(msg["_responseMessages"])
        
    def broadcastText(self, broadcasts, batch=None):
        """ 
        broadcasts is a list of messages in this format: (userId, chatId, text, buttons)
        """
        
        if batch is None:
            batch = []
            
            
        for userId, chatId, text, buttons in broadcasts:
            keyboards = self._formatButtons(buttons)
        
            batch.append(kik.messages.TextMessage(
                to=userId,
                chat_id=chatId,
                body=self._sanitize(self.serv._emojize(text)),
                keyboards=keyboards
                )
            )

        self.__sendBroadcasts(batch)
        
    def sendLink(self, msg, url, buttons=None, text=""):
        keyboards = self._formatButtons(buttons)
    
        if not "_responseMessages" in msg:
            msg["_responseMessages"] = []
            
        if text:
            msg["_responseMessages"].append(kik.messages.LinkMessage(
                to=msg["_userId"],
                chat_id=msg["chatId"],
                url=url,
                text=self.serv._emojize(text),
                keyboards=keyboards
                )
            )
        else:
            msg["_responseMessages"].append(kik.messages.LinkMessage(
                to=msg["_userId"],
                chat_id=msg["chatId"],
                url=url,
                keyboards=keyboards
                )
            )
            
            
        if msg["_responseSent"]:
            # The original message was already sent back, so we need send the reply separately
            self.__sendMessages(msg["_responseMessages"])
            
    def sendPhoto(self, msg, url, buttons=None):
        keyboards = self._formatButtons(buttons)
        
        if not "_responseMessages" in msg:
            msg["_responseMessages"] = []
            
        msg["_responseMessages"].append(kik.messages.PictureMessage(
            to=msg["_userId"],
            chat_id=msg["chatId"],
            pic_url=url,
            keyboards=keyboards
            )
        )
        
        if msg["_responseSent"]:
            # The original message was already sent back, so we need send the reply separately
            self.__sendMessages(msg["_responseMessages"])
    
    
    
    