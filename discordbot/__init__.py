import asyncio
from threading import Thread

# pip
import discord

    
class DiscordBot:
    
    
    specifications = {
        "maxMessageLength" : 2000, # https://discordia.me/server-limits#other-limits
        }
    
    def __init__(self, serv, token, prefix=None):
        """
        prefix - A string or tuple of strings 
        
        """
        self.serv = serv
        self.token = token
        self.client = discord.Client()
        self.prefixes = prefix
        if isinstance(self.prefixes, list):
            self.prefixes = tuple(sorted(self.prefixes, key=len, reverse=True))
        if isinstance(self.prefixes, str) and self.prefixes.strip() == "":
            self.prefixes = None
        
        @self.client.event
        async def on_ready():
            print('DiscordBot logged in')
            
        @self.client.event
        async def on_message(message):
            self.__on_message(message)
            
        @self.client.event
        async def on_server_join(server):
            self.__on_server_join(server)
        
    def run(self):
        def worker(client, loop, token):
            asyncio.set_event_loop(loop)
            client.run(token)
            
        loop = asyncio.get_event_loop()
        t = Thread(target=worker, args=(self.client, loop, self.token))
        t.daemon = True
        t.start()
        
        #self.client.run(self.token)
        
    def __on_server_join(self, server):
        msg = {
            "_bot" : self,
            "_userId" : server.owner.id,
            "text" : "/start",
            "__server" : server
        }
        channels = []
        for channel in server.channels:
            if channel.type == discord.ChannelType.text and channel.permissions_for(server.me).send_messages:
                if channel.name == "general":
                    channel.position = -1
                channels.append(channel)
        
        if channels:
            channels.sort(key=lambda c: c.position)
            msg["__channel"] = channels[0]
            return self.serv._handleTextMessage(msg)
        return
        
        
    def __on_message(self, message):
        if message.author.bot: # Do not reply to bot messages
            return
            
        text = message.content
        
        if self.prefixes is not None:
            if not text.startswith(self.prefixes):
                # Do not reply to message
                return
            else:
                # Remove prefix
                for prefix in self.prefixes:
                    if text.startswith(prefix):
                        text = text[len(prefix):].strip()
                        break
                
        
        msg = {
            "_bot" : self,
            "_userId" : message.author.id,
            "text" : text,
            "__message" : message,
            "__channel" : message.channel
        }
        
        return self.serv._handleTextMessage(msg)
    
    def __formatButtons(self, buttons):
        text = ""
        for button in buttons:
            if isinstance(button[1], str):
                text += "\n%s: %s" % (self.serv._emojize(button[0]), self.serv._emojize(button[1]))
            else:
                text += "\n%s" % (self.serv._emojize(button[0]))
        if text:
            text = "\n" + text
        return text
            
    def sendText(self, msg, text, buttons=None):
        text = self.serv._emojize(text)
        
        if buttons:
            text += self.__formatButtons(buttons)
        
        t = self.client.send_message(msg["__channel"], text)
        asyncio.ensure_future(t)

    def sendLink(self, msg, url, buttons=None, text=""):
        """# Just send the raw URL as text
        
        if text:
            text = url + "\n" + self.serv._emojize(text)
        else:
            text = url
        
        self.sendText(msg, text, buttons)"""
        embed = discord.Embed(title = url, url = url)
        
        if buttons:
            text += self.__formatButtons(buttons)
        
        if text.strip():
            embed.description = text
        
        t = self.client.send_message(msg["__channel"], embed=embed)
        asyncio.ensure_future(t)
        
        
        
    def sendPhoto(self, msg, url, buttons=None):
        embed = discord.Embed(url=url)
        embed.set_image(url=url)
        embed.set_footer(text=url)
        
        if buttons:
            text = self.__formatButtons(buttons)
            embed.description = text
        
        t = self.client.send_message(msg["__channel"], embed=embed)
        asyncio.ensure_future(t)
        
        
