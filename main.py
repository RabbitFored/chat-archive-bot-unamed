from pyrogram import filters, Client
import re
import os
import time 
from pyrogram.errors import FloodWait, BadRequest
from cryptography.fernet import Fernet
import database
import pyrogram
import json
import pyromod.listen
import requests
import ast
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import hashlib
from config import apiID, apiHASH, botTOKEN , encryption_key
from pyrogram import types

fernet = Fernet(encryption_key)

ostrich = Client("ostrich",
                 bot_token=botTOKEN,
                 api_id=apiID,
                 api_hash=apiHASH)

@ostrich.on_message(filters.command(["start"]))
async def start(client, message):

    await message.reply_text(
        text=f"**Hello {message.from_user.mention} 👋 !\n\n"
        "I am backup bot. I can archieve all messages in a chat.**",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("HELP", callback_data="getHelp"),        ]]),
        reply_to_message_id=message.message_id)
    database.scrape(message)
  

async def sender(content,chat):
       if content["type"] == "text":
         if content["data"].get("keyboard"):
              print(content["data"].get("keyboard"))
              
              me = [] 
              for i in content["data"]["keyboard"]:
                  if len(content["data"]["keyboard"][i]) == 0: 
                     return
                  kk = []
                  for j in content["data"]["keyboard"][i]:
                    
                    if len(j) == 0:
                      return
                    q = InlineKeyboardButton(j['text'], url=j['url'])
                    kk.append(q)
                  me.append(kk)
              await ostrich.send_message(chat,content["data"]["text"],reply_markup=InlineKeyboardMarkup(me))
              return

         
         await ostrich.send_message(chat,content["data"]["text"])

       elif content["type"] == "empty":
         # await ostrich.send_message("restrora","empty")  
         pass
       elif content["type"] == "service":
         # await ostrich.send_message("restrora","service")
         pass 
       elif content["type"] == "poll":
         question =  content["data"]["question"]
         options  =  content["data"]["options"]
         poll_type     =  content["data"]["type"]
         is_anonymous  =  content["data"]["is_anonymous"]

         await ostrich.send_poll(chat, question=question,options=options,type=poll_type,is_anonymous=is_anonymous)    
       else:
         if content["data"]["caption"]:
           caption = content["data"]["caption"]
         else:
           caption ="" 
        
         await ostrich.send_cached_media(chat,content["data"]["file_id"],caption=caption)  

@ostrich.on_message(filters.command("restore"))
async def restore(client, message):
    args = message.text.split(" ")
    userid = message.chat.id
    if len(args) > 1:
      id = (args[1])
    else:
      ask_id = await client.ask(userid,"Now send channel id.\n\n**Ex:**`@theostrich`")
      id = ask_id.text
    chat = await client.get_chat(id)
    location = await message.reply_to_message.download()
    with open(location,"rb") as f:
      encrypted = f.read()
      f.close()
    
    decrypted = fernet.decrypt(encrypted)

    backup = json.loads(decrypted.decode("utf-8"))
    owner = backup["chat"]["owner"]
    me    =  await client.get_me()
    chat_id = backup["chat"]["id"]

    hashable =  str(chat_id) + str(owner) + str(me.id) + str(backup["creation"]["date"])
    hash = hashlib.md5(hashable.encode('utf-8'))
    digest = hash.hexdigest()

    if not digest == backup["hash"]:
      await message.reply("Malformed data")
      return

    args = message.text.split(" ") 
    print(len(backup["content"]))
   # if len(args) == 2:
   #  await sender(backup["content"][int(args[1])-1])
   #  return
    for content in backup["content"]:
      try: 
         
         await sender(content,chat.id)
         print(content['message_id'])
     
      except FloodWait as e:
         print(e)
         time.sleep(e.x) 
         await sender(content)
         print(content['message_id'])
         pass
    os.remove(location)                 

    
async def get_owner(chat):
    members = await ostrich.get_chat_members(chat)
    for member in members:
        if member.status == "creator":
          owner = member.user.id
        else:
          pass
    return owner


@ostrich.on_message(filters.command("channels"))
async def channels(client, message):
    userid   = message.chat.id
    channels = await getChannels(userid)
    await message.reply(f'{channels}')

async def getChannels(user):
    channels = database.get_channels(user)
    channel_name = []
    for i in channels:
      chat = await ostrich.get_chat(i)
      if chat.username:
        channel_name.append(chat.username)
      else:
        channel_name.append(chat.first_name)
    return channel_name
   
@ostrich.on_message(filters.command("add"))
async def add_channel(client, message):
   userid   = message.chat.id
   args  = message.text.split(" ")
   if len(args) > 1:
      id = (args[1])
   else:
      ask_id = await client.ask(userid,"Now send channel id.\n\n**Ex:**`@theostrich`")
      id = ask_id.text

   channels = database.get_channels(userid)


   try:
      chat = await client.get_chat(id)
      if chat.id in channels:
        await message.reply("Channel already added in your list. Use /channels to get a list of your channels")
        return
      user = await client.get_chat_member(id,userid)

      if user.status == "creator" or "administrator":
        database.add_channel(userid,chat.id)
        await message.reply("Channel added successfully!")
      else:
        await message.reply("You must be an administrator of the chat to add it here.")

   except BadRequest:
      await message.reply("I have no access to this chat. Make sure to add me as an admin before using this command.")
    


@ostrich.on_message(filters.command("backup"))
async def backup(client, message):
    userid   = message.chat.id
    channels = database.get_channels(userid)
    if len(channels) != 0:
        channel_name = await getChannels(userid)
        buttons = []

        for c in range(len(channel_name)):
            buttons.append([InlineKeyboardButton(channel_name[c], f"bcup{channels[c]}")])
        await message.reply_text(text="**Select a channel:**",
                                 reply_markup=InlineKeyboardMarkup(buttons),
                                 reply_to_message_id=message.message_id)
    else:
        await message.reply("You dont have any channels.\nUse /add to add new channel.")


async def bcup(client, message,channel):
  deletable = await client.send_message(channel,"By @theostrich")
  last_id = deletable.message_id
  await deletable.delete()

  a_list = list(range(1, last_id))
  limit = 200

  content = [] 
  chat = await client.get_chat(channel)
   
# using list comprehension 
  sub_list = [a_list[i:i + limit]           
  for  i in range(0, len(a_list), limit)]
  messages = []

  for scope in sub_list:
    iter_message = await client.get_messages(channel, scope)
    for m in iter_message:
      messages.append(m)

  for m in messages:

      message_id = m.message_id
      type = get_type(m)
      data = get_data(m)    
      c = {
        "message_id" : message_id,
        "type"       : type,
        "data"       : data,
        
      }
      content.append(c)


  owner =  await get_owner(channel)
  me    =  await client.get_me()
  chat_id = message.chat.id
  now = int(time.time())

  hashable =  str(chat_id) + str(owner) + str(me.id) + str(now)
  hash     =  hashlib.md5(hashable.encode('utf-8'))
  digest = hash.hexdigest()

  res = {
      "chat" : {
        "type" : chat.type,
        "id"   : chat_id,
        "owner": owner
               },
     "content"   : content,
     "creation"  : {
        "user"     : message.chat.id,      
        "date"     : now,
        "bot"      : me.username,
                   },
      "hash"  : digest,
      "version" : "0.0.1" 

    }
  
  for line in str((f'{res}').replace('\n','\\n')).splitlines():
        json_dat = json.dumps(ast.literal_eval(line))
        dict_dat = json.loads(json_dat)
        result = json.dumps(dict_dat) 
  with open("backup.json","w") as f:
      f.write(f'{result}')
  with open("backup.json","r") as f:
      co = f.read()
  encrypted = fernet.encrypt(co.encode('utf-8'))
  if chat.username:
     chat_name = chat.username
  elif chat.first_name:
     chat_name = chat.first_name
  else:
     chat_name  = "chat"
  with open(f"{chat_name}.tg","w") as f:
      f.write(f"{encrypted.decode('utf-8')}")
  await message.reply_document(f"{chat_name}.tg")
  os.remove("backup.json")
  os.remove(f"{chat_name}.tg")

        
  
def get_type(m):
  if m.text:
          type = "text" 
  elif m.service:
          type ="service"
  elif m.empty:
          type ="empty"  
  elif m.media:
      if m.photo:
          type= "photo"
      elif m.video:
          type = "video"
      elif m.document:
          type = "document"
      elif m.audio:
          type = "audio"
      elif m.sticker:
          type = "sticker" 
      elif m.animation:
          type = "animation"
      elif m.voice:
          type = "voice"
      elif m.video_note:
          type = "video_note"
      elif m.contact:
          type = "contact"
      elif m.location:
          type = "location" 
      elif m.venue:
          type = "venue" 
      elif m.poll:
          type = "poll" 
      else: 
          type = "invalid" 
  else:
    type = "invalid"  

  return type


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text

rep = {"\n" : "", "\\": ""}

def get_keyboard_data(k):
  print(k)
  ii = json.loads(k)
  ip = {}
  row = {}
  inline_keyboard = ii["inline_keyboard"]
  for io in range(len(inline_keyboard)):
  # [] [] 

    ip[io] = []
    for ij in range(len(inline_keyboard[io])):

     if inline_keyboard[io][ij].get('url'):
     
       ip[io].append(inline_keyboard[io][ij])

  for i in range(len(ip.values())):
    ik = list(ip.values())
    z = []
    for d in ik[i]:
    
    
      vv = { "text" : d['text'] , 
           "url"  : d['url']
           }
      z.append(vv)
    
    row[i] = z
  return row
def get_data(m):
  if m.text:
          data = {
            "text"   :   m.text.html,
                      } 
          
          if m.reply_markup:
             i = get_keyboard_data(str(m.reply_markup))
             data["keyboard"]  =  i
             

  
  elif m.service:
    if m.channel_chat_created:
      data = {
                  "_" : "channel_chat_created"
             }
    elif m.pinned_message:
      data = {
                  "_" : "pinned_message",
                  "message_id" : m.pinned_message.message_id
             }
    elif m.left_chat_member:
      data = {
                  "_" : "left_chat_member"
             }
    elif m.new_chat_title:
      data = {
                  "_" : "new_chat_title"
             }
    elif m.new_chat_photo:
      data = {
                  "_" : "new_chat_photo"
             }
    elif m.delete_chat_photo:
      data = {
                  "_" : "delete_chat_photo"
             }
    elif m.supergroup_chat_created:
      data = {
                  "_" : "supergroup_chat_created"
             }
    elif m.group_chat_created:
      data = {
                  "_" : "group_chat_created"
             }
    elif m.delete_chat_photo:
      data = {
                  "_" : "delete_chat_photo"
             }
    elif m.migrate_from_chat_id:
      data = {
                  "_" : "migrate_from_chat_id"
             }

    else:
         data = None

  elif m.empty:
         data = None
  elif m.poll:
         options = []
         for option in m.poll.options :
           options.append(option.text)
         data = {
            "type"      :  m.poll.type,
            "question"  :  m.poll.question ,
            "options"   :  options,
   "is_anonymous"       : m.poll. is_anonymous ,"allows_multiple_answers" : m.poll.allows_multiple_answers,
            "total_voter_count" : m.poll.total_voter_count
 
         }
  elif m.media:
      if m.photo:
          data = {
                  "file_id" : m.photo.file_id,
                }

          if json.loads(str(m)).get("caption"):
              data["caption"] = m.caption.html

      elif m.video:
          data = {
                  "file_id" : m.video.file_id,
                }

           
          if json.loads(str(m)).get("caption"):
              data["caption"] = m.caption.html
      elif m.document:
          data = {
                  "file_id" : m.document.file_id,
           }
          
          if json.loads(str(m)).get("caption"):
              data["caption"] = m.caption.html
                
      elif m.audio:
          data = {
                  "file_id" : m.audio.file_id,
                }
          
          if json.loads(str(m)).get("caption"):
           data["caption"] = m.caption.html
      elif m.sticker:
          data = {
                  "file_id" : m.sticker.file_id,
                }
      elif m.animation:
          data = {
                  "file_id" : m.animation.file_id,
                }
      elif m.voice:
          data = {
                  "file_id" : m.voice.file_id,
}

          
          if json.loads(str(m)).get("caption"):
              data["caption"] = m.caption.html
      elif m.video_note:
         data = {
                  "file_id" : m.video_note.file_id
                }
      elif m.contact:
         data = {
                  "phone_number " : m.contact.phone_number ,
                  "first_name  " : m.contact.first_name ,
                  "last_name " :  m.contact.last_name,
                  "user_id" : m.contact.user_id,
                  "vcard " : m.contact.vcard,             
                }
      elif m.location:
         data = {
                  "file_id" : m.location.file_id,
                  "date" : m.location.data
                }
      elif m.venue:
         data = {
                  "file_id" : m.venue.file_id,
                  "date" : m.venue.data
                }
      else: 
         data = None
  else:
             data = None
 

  return data

@ostrich.on_callback_query()
async def cb_handler(client, query):
  if query.data.startswith("bcup"):
    channel = query.data[4:]
    await bcup(client,query.message,channel)

ostrich.run()
