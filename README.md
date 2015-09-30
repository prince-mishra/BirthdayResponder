Birthday Responder
==================
For the lazy ones. for those of us who feel a need to thank every birthday post but at the same time feel too lazy to actually do that. No need to put up a single status to thank everyone, use the script to thank everyone individually.

the whole idea of computing is - the machine should work more than the man.

Usage
-----
```python
>> python Responder.py profile_id access_token last_post_id
```

if you don't know or undertand last_post_id, the last command will crawl your entire feed since the beginning of time. So instead of doing that,
```shell
python Responder.py profile_id access_token
```
then give it a few moments to grab a few posts from your feed, then quit the program.
```shell
ctrl+c
```
At this moment, there are a few items from your feed in the db. When you run the program again and it reaches these posts while crawling, it'll stop (post IDs have uniqueness constraint) so you are saved from crawling any further
