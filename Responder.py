__author__ = 'prince'

import requests
from sqlobject import *
import sqlite3 as sqlite
import time
import threading
import sys

class Post(SQLObject):
    post_id = UnicodeCol(length = 1024, unique = True) # lets ensure unique links at db level
    visited = BoolCol(default = False)

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
            self.comment(item.post_id)
            item.visited = True

    def like(self, post_id):
        print "liking : ", post_id
        url = 'https://graph.facebook.com/' + post_id + '/likes?access_token='+self.access_token
        r = requests.post(url)
        print r.json

    def comment(self, post_id):
        print "commenting : ", post_id
        url = 'https://graph.facebook.com/' + post_id + '/comments?access_token='+self.access_token
        message = self.get_message()
        r = requests.post(url, data={'message' : message})
        print r.json

    def get_message(self):
        return "Thanks"

    def run(self):
        while True:
            posts = self.get_unresponsed_posts()
            self.respond(posts)
            time.sleep(30)

class Producer(threading.Thread):
    def __init__(self, url, access_token):
        threading.Thread.__init__(self)
        self.access_token = access_token
        self.url = url
        self.terminate = False

    def insert_item(self, post_id):
        p = Post(post_id = post_id)
        print "inserted : ", p
        return p

    def run(self):
        while True:
            try:
                posts = self.fetch_posts()
                self.insert_posts(posts)
                print "waiting"
                time.sleep(10)
            except Exception:
                pass

    def terminate_condition(self):
        print "resetting"
        self.url = "https://graph.facebook.com/1107033555/feed?access_token="+self.access_token

    def fetch_posts(self):
        print "Fetching"
        r = requests.get(self.url)
        obj = r.json
        return obj

    def insert_posts(self, posts):
        print "inserting"
        if posts.get('data'):
            for item in posts['data']:
                try:
                    self.insert_item(item['id'])
                except Exception, fault:
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
    Usage : python Responder.py access_token last_post_id
    """
    access_token = sys.argv[1]
    connect_db()
    init_db()
    url = "https://graph.facebook.com/1107033555/feed?access_token="+access_token
    try:
        if sys.argv[2]:
            seed = Post(post_id = sys.argv[2])
            # Ugly hack. This ensures that the application resets the url to root url when it hits this post
    except:
        pass
    p = Producer(url = url, access_token = access_token)
    c = Consumer(access_token = access_token)
    p.start()
    c.start()
    p.join()
    c.join()