import pymongo
from config import MongoDB_URI, database, collection

myclient = pymongo.MongoClient(MongoDB_URI)
database = myclient[database]
collection = database[collection]


def scrape(data):
    
    userid = data.from_user.id
    
    firstseen = data.date
    result = collection.find_one({'userid': userid})


    try:
        result['userid']
        userexist = True

    except:
        userexist = False
    print(userexist)
    username = data.from_user.username
    firstname = data.from_user.first_name
    lastname = data.from_user.last_name
    dc = data.from_user.dc_id

    scraped = {}
    scraped['userid'] = userid
    scraped['username'] = username
    scraped['firstname'] = firstname
    scraped['lastname'] = lastname
    scraped['is-banned'] = False
    scraped['dc'] = dc
    scraped['firstseen'] = firstseen

    scraped["channels"] = []

    if (userexist == False):
        collection.insert_one(scraped)



def get_channels(user):
  
  filter = { 'userid': user }  
  
  cursor = collection.find(filter)
  channels = []
  for i in cursor:
    for channel in i["channels"]:
      channels.append(channel)
      
  return channels


def add_channel(user,chat_id): 
  filter = { 'userid': user }
  newvalues = { "$addToSet": { 'channels':chat_id }}
  
  collection.update_one(filter, newvalues)

def delete_channel(user,id):
  filter = {"userid":user}
  values = { "$pull": { "channels":  id}}
  collection.update(filter, values)
 
