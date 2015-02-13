__author__ = 'prince'

import requests
from sqlobject import *
import sqlite3 as sqlite
import time
import threading
import sys
import json

class Post(SQLObject):
    post_id     = UnicodeCol(length = 1024, unique = True) # lets ensure unique links at db level
    visited     = BoolCol(default = False)
    message     = UnicodeCol(length = 8192, default = '') 
    ptype       = UnicodeCol(length = 1024, default = '')
    from_name   = UnicodeCol(length = 1024, default = '')
    from_id     = UnicodeCol(length = 1024, default = '')

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
            self.comment(item.post_id)
            time.sleep(30)
            item.visited = True

    def like(self, post_id):
        print "liking : ", post_id
        
        url = 'https://graph.facebook.com/v2.2/' + post_id + '/likes?access_token='+self.access_token
        print url
        r = requests.post(url)
        print r.content
        
    def comment(self, post_id):
        print "commenting : ", post_id
        url = 'https://graph.facebook.com/v2.2/' + post_id + '/comments?access_token='+self.access_token
        message = self.get_message()
        r = requests.post(url, data={'message' : message})
        print r.content
        

    def get_message(self):
        return "Thanks"

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

    def get_profile_url(self, profileid):
        return "https://graph.facebook.com/" + profileid + "/?access_token="+self.access_token

    def fetch_profile(self, profileid):
        url = self.get_profile_url(profileid)
        r = requests.get(url)
        obj = json.loads(r.content)
        return obj



if __name__=="__main__":
    """
    Usage : python Responder.py profile_id access_token last_post_id
    """
    profile_id = sys.argv[1]
    access_token = sys.argv[2]
    connect_db()
    init_db()
    url = "https://graph.facebook.com/" + profile_id + "/feed?access_token="+access_token
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