#!/usr/bin/python2.4
# -*- coding: utf-8 -*-#
#
# Copyright 2007 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Unit tests for the twitter.py library'''

__author__ = 'dewitt@google.com'

import os
import simplejson
import time
import calendar
import unittest

import twitter
import twitter_pb2

class StatusTest(unittest.TestCase):

  SAMPLE_JSON = '''{"created_at": "Fri Jan 26 23:17:14 +0000 2007", "id": 4391023, "text": "A l\u00e9gp\u00e1rn\u00e1s haj\u00f3m tele van angoln\u00e1kkal.", "user": {"description": "Canvas. JC Penny. Three ninety-eight.", "id": 718443, "location": "Okinawa, Japan", "name": "Kesuke Miyagi", "profile_image_url": "http://twitter.com/system/user/profile_image/718443/normal/kesuke.png", "screen_name": "kesuke", "url": "http://twitter.com/kesuke"}}'''

  def _GetSampleUser(self):
    user = twitter_pb2.User()
    user.id = 718443
    user.name = 'Kesuke Miyagi'
    user.screen_name = 'kesuke'
    user.description = u'Canvas. JC Penny. Three ninety-eight.'
    user.location = 'Okinawa, Japan'
    user.url = 'http://twitter.com/kesuke'
    user.profile.image_url = (
      'http://twitter.com/system/user/profile_image/718443/normal/kesuke.png')
    return user

  def _GetSampleStatus(self):
    status = twitter_pb2.Status()
    status.created_at = 'Fri Jan 26 23:17:14 +0000 2007'
    status.id = 4391023
    status.text = u'A légpárnás hajóm tele van angolnákkal.'
    status.user.CopyFrom(self._GetSampleUser())
    return status

  def testInit(self):
    '''Test the twitter.Status constructor'''
    status = twitter_pb2.Status()
    status.created_at = 'Fri Jan 26 23:17:14 +0000 2007'
    status.id = 4391023
    status.text = u'A légpárnás hajóm tele van angolnákkal.'
    status.user.CopyFrom(self._GetSampleUser())

  def testProperties(self):
    '''Test all of the twitter.Status properties'''
    status = twitter_pb2.Status()
    status.id = 1
    self.assertEqual(1, status.id)
    created_at = calendar.timegm((2007, 1, 26, 23, 17, 14, -1, -1, -1))
    status.created_at = 'Fri Jan 26 23:17:14 +0000 2007'
    self.assertEqual('Fri Jan 26 23:17:14 +0000 2007', status.created_at)
    now = created_at + 10
    self.assertEqual('about 10 seconds ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    status.user.CopyFrom(self._GetSampleUser())
    self.assertEqual(718443, status.user.id)

  def _ParseDate(self, string):
    return calendar.timegm(time.strptime(string, '%b %d %H:%M:%S %Y'))

  def testRelativeCreatedAt(self):
    '''Test various permutations of Status relative_created_at'''
    status = twitter_pb2.Status()
    status.created_at = 'Fri Jan 01 12:00:00 +0000 2007'
    now = self._ParseDate('Jan 01 12:00:00 2007')
    self.assertEqual('about a second ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:00:01 2007')
    self.assertEqual('about a second ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:00:02 2007')
    self.assertEqual('about 2 seconds ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:00:05 2007')
    self.assertEqual('about 5 seconds ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:00:50 2007')
    self.assertEqual('about a minute ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:01:00 2007')
    self.assertEqual('about a minute ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:01:10 2007')
    self.assertEqual('about a minute ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:02:00 2007')
    self.assertEqual('about 2 minutes ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:31:50 2007')
    self.assertEqual('about 31 minutes ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 12:50:00 2007')
    self.assertEqual('about an hour ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 13:00:00 2007')
    self.assertEqual('about an hour ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 13:10:00 2007')
    self.assertEqual('about an hour ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 14:00:00 2007')
    self.assertEqual('about 2 hours ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 01 19:00:00 2007')
    self.assertEqual('about 7 hours ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 02 11:30:00 2007')
    self.assertEqual('about a day ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Jan 04 12:00:00 2007')
    self.assertEqual('about 3 days ago',
                     twitter.ComputeRelativeCreatedAt(status, now))
    now = self._ParseDate('Feb 04 12:00:00 2007')
    self.assertEqual('about 34 days ago',
                     twitter.ComputeRelativeCreatedAt(status, now))

  def testEq(self):
    '''Test the twitter.Status __eq__ method'''
    status = twitter_pb2.Status()
    status.created_at = 'Fri Jan 26 23:17:14 +0000 2007'
    status.id = 4391023
    status.text = u'A légpárnás hajóm tele van angolnákkal.'
    status.user.CopyFrom(self._GetSampleUser())
    self.assertEqual(status, self._GetSampleStatus())

  def testNewFromJsonDict(self):
    '''Test the twitter.Status NewFromJsonDict method'''
    data = simplejson.loads(StatusTest.SAMPLE_JSON)
    status = twitter.NewStatusFromJsonDict(data)
    self.assertEqual(self._GetSampleStatus(), status)


class UserTest(unittest.TestCase):

  SAMPLE_JSON = '''{"description": "Indeterminate things", "id": 673483, "location": "San Francisco, CA", "name": "DeWitt", "profile_image_url": "http://twitter.com/system/user/profile_image/673483/normal/me.jpg", "screen_name": "dewitt", "status": {"created_at": "Fri Jan 26 17:28:19 +0000 2007", "id": 4212713, "text": "\\"Select all\\" and archive your Gmail inbox.  The page loads so much faster!"}, "url": "http://unto.net/"}'''

  def _GetSampleStatus(self):
    status = twitter_pb2.Status()
    status.created_at = 'Fri Jan 26 17:28:19 +0000 2007'
    status.id = 4212713
    status.text = (
      '"Select all" and archive your Gmail inbox.  The page loads so much faster!')
    return status

  def _GetSampleUser(self):
    user = twitter_pb2.User()
    user.id = 673483
    user.name = 'DeWitt'
    user.screen_name = 'dewitt'
    user.description = u'Indeterminate things'
    user.location = 'San Francisco, CA'
    user.url = 'http://unto.net/'
    user.profile.image_url = (
      'http://twitter.com/system/user/profile_image/673483/normal/me.jpg')
    user.status.CopyFrom(self._GetSampleStatus())
    return user

  def testInit(self):
    '''Test the twitter.User constructor'''
    user = twitter_pb2.User()
    user.id = 673483
    user.name = 'DeWitt'
    user.screen_name = 'dewitt'
    user.description = u'Indeterminate things'
    user.location = 'San Francisco, CA'
    user.url = 'http://unto.net/'
    user.profile.image_url = (
      'http://twitter.com/system/user/profile_image/673483/normal/me.jpg')
    user.status.CopyFrom(self._GetSampleStatus())

  def testProperties(self):
    '''Test all of the twitter.User properties'''
    user = twitter_pb2.User()
    user.id = 673483
    self.assertEqual(673483, user.id)
    user.name = 'DeWitt'
    self.assertEqual('DeWitt', user.name)
    user.screen_name = 'dewitt'
    self.assertEqual('dewitt', user.screen_name)
    user.description = 'Indeterminate things'
    self.assertEqual('Indeterminate things', user.description)
    user.location = 'San Francisco, CA'
    self.assertEqual('San Francisco, CA', user.location)
    user.profile.image_url = (
      'http://twitter.com/system/user/profile_image/673483/normal/me.jpg')
    self.assertEqual(
      'http://twitter.com/system/user/profile_image/673483/normal/me.jpg',
      user.profile.image_url)
    self.status = self._GetSampleStatus()
    self.assertEqual(4212713, self.status.id)

  def testEq(self):
    '''Test the twitter.User __eq__ method'''
    user = twitter_pb2.User()
    user.id = 673483
    user.name = 'DeWitt'
    user.screen_name = 'dewitt'
    user.description = 'Indeterminate things'
    user.location = 'San Francisco, CA'
    user.profile.image_url = (
      'http://twitter.com/system/user/profile_image/673483/normal/me.jpg')
    user.url = 'http://unto.net/'
    user.status.CopyFrom(self._GetSampleStatus())
    self.assertEqual(user, self._GetSampleUser())

  def testNewFromJsonDict(self):
    '''Test the twitter.User NewFromJsonDict method'''
    data = simplejson.loads(UserTest.SAMPLE_JSON)
    user = twitter.NewUserFromJsonDict(data)
    self.assertEqual(self._GetSampleUser(), user)


class ResultsTest(unittest.TestCase):

  SAMPLE_JSON = '''{"results":[{"text":"is loving how on twitter all these crazy popular celebraties seem like regular people like me &amp; you....i &lt;3 twitter","to_user_id":null,"from_user":"oxAly","id":1818791702,"from_user_id":6905503,"iso_language_code":"en","source":"&lt;a href=&quot;http:\/\/twitter.com\/&quot;&gt;web&lt;\/a&gt;","profile_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_images\/212410949\/mommy__me_normal.jpg","created_at":"Sat, 16 May 2009 18:59:22 +0000"},{"text":"@ryanjoy what are u using for twitter nowadays... Twitterfon just added ads and the new update is no bueno","to_user_id":1002058,"to_user":"ryanjoy","from_user":"Tyler_Batten","id":1818791671,"from_user_id":2178043,"iso_language_code":"en","source":"&lt;a href=&quot;http:\/\/twitterfon.net\/&quot;&gt;TwitterFon&lt;\/a&gt;","profile_image_url":"http:\/\/s3.amazonaws.com\/twitter_production\/profile_images\/62948019\/Photo_249_normal.jpg","created_at":"Sat, 16 May 2009 18:59:22 +0000"}],"since_id":0,"max_id":1818791702,"refresh_url":"?since_id=1818791702&q=twitter","results_per_page":2,"next_page":"?page=2&max_id=1818791702&rpp=2&q=twitter","completed_in":0.016569,"page":1,"query":"twitter"}'''

  def testNewResultsFromJsonDict(self):
    data = simplejson.loads(ResultsTest.SAMPLE_JSON)
    results = twitter.NewResultsFromJsonDict(data)
    self.assertEqual(0.016569, results.completed_in)
    self.assertEqual(1818791702, results.max_id)
    self.assertEqual('?page=2&max_id=1818791702&rpp=2&q=twitter',
                     results.next_page)
    self.assertEqual(1, results.page)
    self.assertEqual('twitter', results.query)
    self.assertEqual('?since_id=1818791702&q=twitter',
                     results.refresh_url)
    self.assertEqual(2, results.results_per_page)
    self.assertEqual(0, results.since_id)
    self.assertEqual(2, len(results.results))
    result = results.results[0]
    self.assertEqual('Sat, 16 May 2009 18:59:22 +0000', result.created_at)
    self.assertEqual('oxAly', result.from_user)
    self.assertEqual(6905503, result.from_user_id)
    self.assertEqual(1818791702, result.id)
    self.assertEqual('en', result.iso_language_code)
    self.assertFalse(result.HasField('to_user_id'))
    self.assertEqual('''is loving how on twitter all these crazy popular celebraties seem like regular people like me &amp; you....i &lt;3 twitter''',
                     result.text)
    result = results.results[1]
    self.assertEqual(1818791671, result.id)
    self.assertEqual(1002058, result.to_user_id)
    self.assertEqual('ryanjoy', result.to_user)


class FileCacheTest(unittest.TestCase):

  def testInit(self):
    """Test the twitter._FileCache constructor"""
    cache = twitter._FileCache()
    self.assert_(cache is not None, 'cache is None')

  def testSet(self):
    """Test the twitter._FileCache.Set method"""
    cache = twitter._FileCache()
    cache.Set("foo",'Hello World!')
    cache.Remove("foo")

  def testRemove(self):
    """Test the twitter._FileCache.Remove method"""
    cache = twitter._FileCache()
    cache.Set("foo",'Hello World!')
    cache.Remove("foo")
    data = cache.Get("foo")
    self.assertEqual(data, None, 'data is not None')

  def testGet(self):
    """Test the twitter._FileCache.Get method"""
    cache = twitter._FileCache()
    cache.Set("foo",'Hello World!')
    data = cache.Get("foo")
    self.assertEqual('Hello World!', data)
    cache.Remove("foo")

  def testGetCachedTime(self):
    """Test the twitter._FileCache.GetCachedTime method"""
    now = time.time()
    cache = twitter._FileCache()
    cache.Set("foo",'Hello World!')
    cached_time = cache.GetCachedTime("foo")
    delta = cached_time - now
    self.assert_(delta <= 1,
                 'Cached time differs from clock time by more than 1 second.')
    cache.Remove("foo")

class ApiTest(unittest.TestCase):

  def setUp(self):
    self._urllib = MockUrllib()
    api = twitter.Api(username='test', password='test', cache=None)
    api.SetUrllib(self._urllib)
    self._api = api

  def testTwitterError(self):
    '''Test that twitter responses containing an error message are wrapped.'''
    self._AddHandler('http://twitter.com/statuses/public_timeline.json',
                     curry(self._OpenTestData, 'public_timeline_error.json'))
    # Manually try/catch so we can check the exception's value
    try:
      statuses = self._api.GetPublicTimeline()
    except twitter.TwitterError, error:
      # If the error message matches, the test passes
      self.assertEqual('test error', error.message)
    else:
      self.fail('TwitterError expected')

  def testGetPublicTimeline(self):
    '''Test the twitter.Api GetPublicTimeline method'''
    self._AddHandler('http://twitter.com/statuses/public_timeline.json?since_id=12345',
                     curry(self._OpenTestData, 'public_timeline.json'))
    statuses = self._api.GetPublicTimeline(since_id=12345)
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(20, len(statuses))
    self.assertEqual(89497702, statuses[0].id)

  def testGetUserTimeline(self):
    '''Test the twitter.Api GetUserTimeline method'''
    self._AddHandler(
        'http://twitter.com/statuses/user_timeline/kesuke.json?count=1',
        curry(self._OpenTestData, 'user_timeline-kesuke.json'))
    statuses = self._api.GetUserTimeline('kesuke', count=1)
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(89512102, statuses[0].id)
    self.assertEqual(718443, statuses[0].user.id)

  def testGetFriendsTimeline(self):
    '''Test the twitter.Api GetFriendsTimeline method'''
    self._AddHandler('http://twitter.com/statuses/friends_timeline/kesuke.json',
                     curry(self._OpenTestData, 'friends_timeline-kesuke.json'))
    statuses = self._api.GetFriendsTimeline('kesuke')
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(20, len(statuses))
    self.assertEqual(718443, statuses[0].user.id)

  def testGetStatus(self):
    '''Test the twitter.Api GetStatus method'''
    self._AddHandler('http://twitter.com/statuses/show/89512102.json',
                     curry(self._OpenTestData, 'show-89512102.json'))
    status = self._api.GetStatus(89512102)
    self.assertEqual(89512102, status.id)
    self.assertEqual(718443, status.user.id)

  def testDestroyStatus(self):
    '''Test the twitter.Api DestroyStatus method'''
    self._AddHandler('http://twitter.com/statuses/destroy/103208352.json',
                     curry(self._OpenTestData, 'status-destroy.json'))
    status = self._api.DestroyStatus(103208352)
    self.assertEqual(103208352, status.id)

  def testPostUpdate(self):
    '''Test the twitter.Api PostUpdate method'''
    self._AddHandler('http://twitter.com/statuses/update.json',
                     curry(self._OpenTestData, 'update.json'))
    status = self._api.PostUpdate(u'Моё судно на воздушной подушке полно угрей')
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(u'Моё судно на воздушной подушке полно угрей', status.text)

  def testAciiStatusLength(self):
    '''Test the length check of ascii status updates'''
    self._AddHandler('http://twitter.com/statuses/update.json',
                     curry(self._OpenTestData, 'update.json'))
    # Post 140 characters of ascii text
    status = self._api.PostUpdate('abcdefghij' * 14)
    # Post 141 characters of ascii text
    try:
      status = self._api.PostUpdate(('abcdefghij' * 14) + 'k')
    except twitter.TwitterError:
      pass  # expected
    else:
      self.fail('TwitterError expected')

  def testUnicodeStatusLength(self):
    '''Test the length check of ascii status updates'''
    self._AddHandler('http://twitter.com/statuses/update.json',
                     curry(self._OpenTestData, 'update.json'))
    # Post 140 characters of unicode text
    status = self._api.PostUpdate(u'абвгдежзий' * 14)
    # Post 141 characters of unicode text
    try:
      status = self._api.PostUpdate((u'абвгдежзий' * 14) + u'к')
    except twitter.TwitterError:
      pass  # expected
    else:
      self.fail('TwitterError expected')


  def testGetReplies(self):
    '''Test the twitter.Api GetReplies method'''
    self._AddHandler('http://twitter.com/statuses/replies.json?page=1',
                     curry(self._OpenTestData, 'replies.json'))
    statuses = self._api.GetReplies(page=1)
    self.assertEqual(36657062, statuses[0].id)

  def testGetFriends(self):
    '''Test the twitter.Api GetFriends method'''
    self._AddHandler('http://twitter.com/statuses/friends.json?page=1',
                     curry(self._OpenTestData, 'friends.json'))
    users = self._api.GetFriends(page=1)
    buzz = [u.status for u in users if u.screen_name == 'buzz']
    self.assertEqual(89543882, buzz[0].id)

  def testGetFollowers(self):
    '''Test the twitter.Api GetFollowers method'''
    self._AddHandler('http://twitter.com/statuses/followers.json?page=1',
                     curry(self._OpenTestData, 'followers.json'))
    users = self._api.GetFollowers(page=1)
    # This is rather arbitrary, but spot checking is better than nothing
    alexkingorg = [u.status for u in users if u.screen_name == 'alexkingorg']
    self.assertEqual(89554432, alexkingorg[0].id)

  def testGetFeatured(self):
    '''Test the twitter.Api GetFeatured method'''
    self._AddHandler('http://twitter.com/statuses/featured.json',
                     curry(self._OpenTestData, 'featured.json'))
    users = self._api.GetFeatured()
    # This is rather arbitrary, but spot checking is better than nothing
    stevenwright = [u.status for u in users if u.screen_name == 'stevenwright']
    self.assertEqual(86991742, stevenwright[0].id)

  def testGetDirectMessages(self):
    '''Test the twitter.Api GetDirectMessages method'''
    self._AddHandler('http://twitter.com/direct_messages.json?page=1',
                     curry(self._OpenTestData, 'direct_messages.json'))
    statuses = self._api.GetDirectMessages(page=1)
    self.assertEqual(u'A légpárnás hajóm tele van angolnákkal.', statuses[0].text)

  def testPostDirectMessage(self):
    '''Test the twitter.Api PostDirectMessage method'''
    self._AddHandler('http://twitter.com/direct_messages/new.json',
                     curry(self._OpenTestData, 'direct_messages-new.json'))
    status = self._api.PostDirectMessage('test', u'Моё судно на воздушной подушке полно угрей')
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(u'Моё судно на воздушной подушке полно угрей', status.text)

  def testDestroyDirectMessage(self):
    '''Test the twitter.Api DestroyDirectMessage method'''
    self._AddHandler('http://twitter.com/direct_messages/destroy/3496342.json',
                     curry(self._OpenTestData, 'direct_message-destroy.json'))
    status = self._api.DestroyDirectMessage(3496342)
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(673483, status.sender_id)

  def testCreateFriendship(self):
    '''Test the twitter.Api CreateFriendship method'''
    self._AddHandler('http://twitter.com/friendships/create/dewitt.json',
                     curry(self._OpenTestData, 'friendship-create.json'))
    user = self._api.CreateFriendship('dewitt')
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(673483, user.id)

  def testDestroyFriendship(self):
    '''Test the twitter.Api DestroyFriendship method'''
    self._AddHandler('http://twitter.com/friendships/destroy/dewitt.json',
                     curry(self._OpenTestData, 'friendship-destroy.json'))
    user = self._api.DestroyFriendship('dewitt')
    # This is rather arbitrary, but spot checking is better than nothing
    self.assertEqual(673483, user.id)

  def testGetUser(self):
    '''Test the twitter.Api GetUser method'''
    self._AddHandler('http://twitter.com/users/show/dewitt.json',
                     curry(self._OpenTestData, 'show-dewitt.json'))
    user = self._api.GetUser('dewitt')
    self.assertEqual('dewitt', user.screen_name)
    self.assertEqual(89586072, user.status.id)

  def testSearch(self):
    '''Test the Twitter.Api Search method'''
    self._AddHandler('http://search.twitter.com/search.json?q=twitter',
                     curry(self._OpenTestData, 'search.json'))
    results = self._api.Search('twitter')
    self.assertEqual(10, len(results.results))

  def testShowFriendships(self):
    '''Test the Twitter.Api ShowFriendships method'''
    self._AddHandler(
      'http://twitter.com/friendships/show.json' +
      '?target_screen_name=ev' +
      '&source_screen_name=dewitt',
      curry(self._OpenTestData, 'show_friendships.json'))
    relationship = self._api.ShowFriendships(
        source_screen_name='dewitt', target_screen_name='ev')
    self.assertTrue(relationship != None)
    self.assertTrue(relationship._has_source)
    self.assertTrue(relationship._has_target)
    self.assertEqual(True, relationship.target.following)
    self.assertEqual(True, relationship.target.followed_by)
    self.assertEqual(20, relationship.target.id)
    self.assertEqual('ev', relationship.target.screen_name)
    self.assertEqual(False, relationship.source.notifications_enabled)
    self.assertEqual(False, relationship.source.blocking)
    self.assertEqual(True, relationship.source.following)
    self.assertEqual(True, relationship.source.followed_by)
    self.assertEqual(673483, relationship.source.id)
    self.assertEqual('dewitt', relationship.source.screen_name)
    
  def _AddHandler(self, url, callback):
    self._urllib.AddHandler(url, callback)

  def _GetTestDataPath(self, filename):
    directory = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(directory, 'testdata')
    return os.path.join(test_data_dir, filename)

  def _OpenTestData(self, filename):
    return open(self._GetTestDataPath(filename))

class MockUrllib(object):
  '''A mock replacement for urllib that hardcodes specific responses.'''

  def __init__(self):
    self._handlers = {}
    self.HTTPBasicAuthHandler = MockHTTPBasicAuthHandler

  def AddHandler(self, url, callback):
    self._handlers[url] = callback

  def build_opener(self, *handlers):
    return MockOpener(self._handlers)

class MockOpener(object):
  '''A mock opener for urllib'''

  def __init__(self, handlers):
    self._handlers = handlers
    self._opened = False

  def open(self, url, data=None):
    if self._opened:
      raise Exception('MockOpener already opened.')
    if url in self._handlers:
      self._opened = True
      return self._handlers[url]()
    else:
      raise Exception('Unexpected URL %s' % url)

  def close(self):
    if not self._opened:
      raise Exception('MockOpener closed before it was opened.')
    self._opened = False

class MockHTTPBasicAuthHandler(object):
  '''A mock replacement for HTTPBasicAuthHandler'''

  def add_password(self, realm, uri, user, passwd):
    # TODO(dewitt): Add verification that the proper args are passed
    pass

class curry:
  # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52549

  def __init__(self, fun, *args, **kwargs):
    self.fun = fun
    self.pending = args[:]
    self.kwargs = kwargs.copy()

  def __call__(self, *args, **kwargs):
    if kwargs and self.kwargs:
      kw = self.kwargs.copy()
      kw.update(kwargs)
    else:
      kw = kwargs or self.kwargs
    return self.fun(*(self.pending + args), **kw)


def suite():
  suite = unittest.TestSuite()
  suite.addTests(unittest.makeSuite(FileCacheTest))
  suite.addTests(unittest.makeSuite(StatusTest))
  suite.addTests(unittest.makeSuite(UserTest))
  suite.addTests(unittest.makeSuite(ApiTest))
  return suite

if __name__ == '__main__':
  unittest.main()
