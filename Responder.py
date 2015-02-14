__author__ = 'prince'

import requests
from sqlobject import *
import sqlite3 as sqlite
import time
import threading
import sys
import json
import random

class Post(SQLObject):
    post_id     = UnicodeCol(length = 1024, unique = True) # lets ensure unique links at db level
    visited     = BoolCol(default = False)
    message     = UnicodeCol(length = 8192, default = '')
    ptype       = UnicodeCol(length = 1024, default = '')
    from_name   = UnicodeCol(length = 1024, default = '')
    from_id     = UnicodeCol(length = 1024, default = '')

class MessagePool():
    def __init__(self):
        self.messages = ["Hey Thanks %s. How is life at your end?",
        "Thank you so much %s. Hope you had a great day too.",
        "Thanks %s for wishing! How did your day go?",
        "Dhanyawaad %s! kya haal chaal?",
        "%s Thank you so much! How are you?",
        "Thank you %s. What are you upto these days?",
        "%s haardik abhinandan ;-)",
        "Thanks a lot %s. Howz you?",
        "Thank you %s!"]

    def get_random_index(self):
        return random.randint(0,len(self.messages)-1)

    def get_message(self, person_name):
        return self.messages[self.get_random_index()] % person_name

def connect_db():
        connection_string = 'sqlite:' + 'responder.db'
        connection = connectionForURI(connection_string)
        sqlhub.processConnection = connection

def init_db():
    Post.createTable(ifNotExists=True)

class Consumer(threading.Thread):
    def __init__(self, access_token):
        threading.Thread.__init__(self)
        self.access_token = access_token
        self.msg_pool = MessagePool()

    def get_unresponsed_posts(self):
        print "Getting unresponded posts"
        posts = list(Post.select(Post.q.visited == False))
        #TODO: fuzzy match post to ensure its a birthday wish and respond only to those
        return posts

    def respond(self, posts):
        print "Posts to respond : ", posts
        for item in posts:
            self.like(item.post_id)
            time.sleep(30)
            self.comment(item.post_id, item.from_name)
            time.sleep(30)
            item.visited = True

    def like(self, post_id):
        print "liking : ", post_id

        url = 'https://graph.facebook.com/v2.2/' + post_id + '/likes?access_token='+self.access_token
        print url
        r = requests.post(url)
        print r.content

    def comment(self, post_id, person_name):
        print "commenting : ", post_id
        url = 'https://graph.facebook.com/v2.2/' + post_id + '/comments?access_token='+self.access_token
        message = self.get_message(person_name)
        print message
        r = requests.post(url, data={'message' : message})
        print r.content


    def get_message(self, person_name):
        return self.msg_pool.get_message(person_name)

    def run(self):
        while True:
            posts = self.get_unresponsed_posts()
            self.respond(posts)
            print "consumer waiting"
            time.sleep(300)

class Producer(threading.Thread):
    def __init__(self, url, profile_id, access_token):
        threading.Thread.__init__(self)
        self.access_token = access_token
        self.url = url
        self.profile_id = profile_id
        self.terminate = False

    def insert_item(self, item):
        from_user = item.get('from')
        if from_user['id'] == profile_id:
            return
        p = Post(post_id = item['id'], message = item.get('message', ''), ptype=item.get('type', ''), from_id=from_user.get('id', ''), from_name=from_user.get('name', ''))
        print "inserted : ", p
        return p

    def run(self):
        while True:
            try:
                posts = self.fetch_posts()
                self.insert_posts(posts)
                print "producer waiting"
                time.sleep(30)
            except Exception:
                pass

    def terminate_condition(self):
        print "resetting"
        self.url = "https://graph.facebook.com/" + self.profile_id + "/feed?access_token="+self.access_token

    def fetch_posts(self):
        print "Fetching : ", self.url
        r = requests.get(self.url)
        obj = json.loads(r.content)
        return obj

    def insert_posts(self, posts):
        print "\n\ninserting :"
        if posts.get('data'):
            print "\nposts : ", len(posts['data'])
            for item in posts['data']:
                try:
                    self.insert_item(item)
                except Exception, fault:
                    print "Error in insert_posts. item : %s Error : %s" % (item, str(fault))
                    self.terminate_condition()
                    break
            else:
                if posts.get('paging'):
                    next_url = posts['paging']['next']
                    self.url = next_url + '&access_token=' + self.access_token
                else:
                    self.terminate_condition()



if __name__=="__main__":
    """
    Usage : python Responder.py profile_id access_token last_post_id
    """
    profile_id = sys.argv[1]
    access_token = sys.argv[2]
    connect_db()
    init_db()
    url = "https://graph.facebook.com/" + profile_id + "/feed?limit=250&access_token="+access_token
    try:
        if sys.argv[3]:
            seed = Post(post_id = sys.argv[3])
            # Ugly hack. This ensures that the application resets the url to root url when it hits this post
    except:
        pass
    p = Producer(url = url, profile_id = profile_id, access_token = access_token)
    c = Consumer(access_token = access_token)
    p.start()
    c.start()
    p.join()
    c.join()
