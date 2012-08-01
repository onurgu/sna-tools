#!/usr/bin/python2.4
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

'''A library that provides a python interface to the Twitter API'''

__author__ = 'dewitt@google.com'
__version__ = '0.6-devel'
__branch__ = 'dev'


import base64
import calendar
import os
import rfc822
import simplejson
import sys
import tempfile
import textwrap
import time
import httplib
import urllib
import urllib2
import urlparse

import twitter_pb2

try:
  from hashlib import md5
except ImportError:
  from md5 import md5


CHARACTER_LIMIT = 140

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()


class TwitterError(Exception):
  '''Base class for Twitter errors'''

  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


def _CopyProperty(source, destination, name, destination_name=None):
  '''Optionally copies a property from source to destination.

  Properties will be copied if and only if they appear in the dict
  and are not None.

  Args:
    source: A python dict
    destination: A python object with a property accessor
    name: The name of the source property
    destination_name: The name of the destination property, if different from name
  '''
  if destination_name is None:
    destination_name = name
  try:
    value = source[name]
    if value is not None:
      # If the destination_name has one or more '.' in it
      # traverse the destination object downward to find
      # the actual destination object and property name
      parts = destination_name.split('.')
      for part in parts[0:-1]:
        destination = getattr(destination, part)
        destination_name = parts[-1]
      setattr(destination, destination_name, value)
  except KeyError:
    # source property not found
    pass


def NewStatusFromJsonDict(data):
  '''Create a new Status instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A Status instance
  '''
  status = twitter_pb2.Status()
  _CopyProperty(data, status, 'created_at')
  _CopyProperty(data, status, 'favorited')
  _CopyProperty(data, status, 'id')
  _CopyProperty(data, status, 'text')
  _CopyProperty(data, status, 'in_reply_to_screen_name')
  _CopyProperty(data, status, 'in_reply_to_user_id')
  _CopyProperty(data, status, 'in_reply_to_status_id')
  _CopyProperty(data, status, 'truncated')
  _CopyProperty(data, status, 'source')
  if 'user' in data:
    status.user.CopyFrom(NewUserFromJsonDict(data['user']))
  return status


def NewRelationshipFromJsonDict(data):
  '''Create a new Relationship instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A Relationship instance
  '''
  relationship = twitter_pb2.Relationship()
  if 'relationship' not in data:
    return None
  relationship_data = data['relationship']
  if 'source' in relationship_data:
    relationship.source.CopyFrom(
        NewRelationshipUserFromJsonDict(relationship_data['source']))
  if 'target' in relationship_data:
    relationship.target.CopyFrom(
        NewRelationshipUserFromJsonDict(relationship_data['target']))
  return relationship


def NewRelationshipUserFromJsonDict(data):
  '''Create a new Relationship.User instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A Relationship.User instance
  '''
  user = twitter_pb2.Relationship.User()
  _CopyProperty(data, user, 'id')
  _CopyProperty(data, user, 'screen_name')
  _CopyProperty(data, user, 'following')
  _CopyProperty(data, user, 'followed_by')
  _CopyProperty(data, user, 'notifications_enabled')
  _CopyProperty(data, user, 'blocking')
  return user


def ComputeCreatedAtInSeconds(status):
  '''Returns the number of seconds past the epoch in the current timezone.

  Args:
    status: A status instance
  Returns:
    The number of seconds since the status was created.
  '''
  return calendar.timegm(rfc822.parsedate(status.created_at))


def ComputeRelativeCreatedAt(status, now=None):
  '''Get a human redable string representing the posting time

  Args:
    status: A status instance
    now:
      The current time, if the client choses to set it.  Defaults
      to the wall clock time.
  Returns:
    A human readable string representing the posting time
    '''
  if now is None:
    now = time.time()
  fudge = 1.25
  created_at_in_seconds = ComputeCreatedAtInSeconds(status)
  delta = long(now) - long(created_at_in_seconds)
  if delta < (1 * fudge):
    return 'about a second ago'
  elif delta < (60 * (1/fudge)):
    return 'about %d seconds ago' % (delta)
  elif delta < (60 * fudge):
    return 'about a minute ago'
  elif delta < (60 * 60 * (1/fudge)):
    return 'about %d minutes ago' % (delta / 60)
  elif delta < (60 * 60 * fudge):
    return 'about an hour ago'
  elif delta < (60 * 60 * 24 * (1/fudge)):
    return 'about %d hours ago' % (delta / (60 * 60))
  elif delta < (60 * 60 * 24 * fudge):
    return 'about a day ago'
  else:
    return 'about %d days ago' % (delta / (60 * 60 * 24))


def NewUserFromJsonDict(data):
  '''Create a new User instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A User instance
  '''
  user = twitter_pb2.User()
  _CopyProperty(data, user, 'id')
  _CopyProperty(data, user, 'name')
  _CopyProperty(data, user, 'screen_name')
  _CopyProperty(data, user, 'location')
  _CopyProperty(data, user, 'description')
  _CopyProperty(data, user, 'statuses_count')
  _CopyProperty(data, user, 'followers_count')
  _CopyProperty(data, user, 'favourites_count', 'favorites_count')
  _CopyProperty(data, user, 'friends_count')
  _CopyProperty(data, user, 'profile_image_url', 'profile.image_url')
  _CopyProperty(data, user, 'profile_background_tile', 'profile.background_tile')
  _CopyProperty(data, user, 'profile_background_image_url', 'profile.background_image_url')
  _CopyProperty(data, user, 'profile_sidebar_fill_color', 'profile.sidebar_fill_color')
  _CopyProperty(data, user, 'profile_background_color', 'profile.background_color')
  _CopyProperty(data, user, 'profile_link_color', 'profile.link_color')
  _CopyProperty(data, user, 'profile_text_color', 'profile.text_color')
  _CopyProperty(data, user, 'protected')
  _CopyProperty(data, user, 'utc_offset')
  _CopyProperty(data, user, 'time_zone')
  _CopyProperty(data, user, 'url')
  if 'status' in data:
    user.status.CopyFrom(NewStatusFromJsonDict(data['status']))
  return user


def NewDirectMessageFromJsonDict(data):
  '''Create a new DirectMessage instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A DirectMessage instance
  '''
  direct_message = twitter_pb2.DirectMessage()
  _CopyProperty(data, direct_message, 'created_at')
  _CopyProperty(data, direct_message, 'recipient_id')
  _CopyProperty(data, direct_message, 'sender_id')
  _CopyProperty(data, direct_message, 'text')
  _CopyProperty(data, direct_message, 'sender_screen_name')
  _CopyProperty(data, direct_message, 'id')
  _CopyProperty(data, direct_message, 'recipient_screen_name')
  return direct_message


def NewResultsFromJsonDict(data):
  '''Create a new Results instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A Results instance
  '''
  results = twitter_pb2.Results()
  _CopyProperty(data, results, 'completed_in')
  _CopyProperty(data, results, 'max_id')
  _CopyProperty(data, results, 'next_page')
  _CopyProperty(data, results, 'page')
  _CopyProperty(data, results, 'query')
  _CopyProperty(data, results, 'refresh_url')
  _CopyProperty(data, results, 'since_id')
  _CopyProperty(data, results, 'results_per_page')
  if 'results' in data:
    for result_data in data['results']:
      result = results.results.add()
      result.CopyFrom(NewResultFromJsonDict(result_data))
  return results


def NewResultFromJsonDict(data):
  '''Create a new Result instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A Result instance
  '''
  result = twitter_pb2.Results.Result()
  _CopyProperty(data, result, 'created_at')
  _CopyProperty(data, result, 'from_user')
  _CopyProperty(data, result, 'from_user_id')
  _CopyProperty(data, result, 'id')
  _CopyProperty(data, result, 'iso_language_code')
  _CopyProperty(data, result, 'profile_image_url')
  _CopyProperty(data, result, 'source')
  _CopyProperty(data, result, 'text')
  _CopyProperty(data, result, 'to_user')
  _CopyProperty(data, result, 'to_user_id')
  return result

def NewListFromJsonDict(data):
  '''Create a new List instance based on a JSON dict.

  Args:
    data: A JSON dict, as parsed from a twitter API response
  Returns:
    A List instance
  '''
  result = twitter_pb2.List()
  _CopyProperty(data, result, 'member_count')
  _CopyProperty(data, result, 'name')
  _CopyProperty(data, result, 'subscriber_count')
  _CopyProperty(data, result, 'uri')
  _CopyProperty(data, result, 'slug')
  _CopyProperty(data, result, 'full_name')
  _CopyProperty(data, result, 'full_name')
  _CopyProperty(data, result, 'id')
  if 'user' in data:
    result.user.CopyFrom(NewUserFromJsonDict(data['user']))
  return result

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    username and password:

      >>> api = twitter.Api(username='twitter user', password='twitter pass')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFavorites(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)

    Recently introduced list methods:

      >>> api.GetUserLists(user, cursor)
      >>> api.GetListMembers(list_slug, user, cursor)
      >>> api.GetList(list_slug, user)

    Example usage of lists:

      >>> api = twitter.Api(username="", password="")
      >>> members = api.GetListMembers('list_slug')
      >>> members['users'][0].screen_name
      >>> members = api.GetListMembers('list_slug', cursor=members['next_cursor'])
      >>> members['users'][0].screen_name
      >>> list = api.GetList('list_slug')
      >>> list.member_count
      >>> lists = api.GetUserLists()
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute

  _API_REALM = 'Twitter API'

  def __init__(self,
               username=None,
               password=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE):
    '''Instantiate a new twitter.Api object.

    Args:
      username: The username of the twitter account.  [optional]
      password: The password for the twitter account. [optional]
      input_encoding: The encoding used to encode input strings. [optional]
      request_header: A dictionary of additional HTTP request headers. [optional]
      cache:
          The cache instance to use. Defaults to DEFAULT_CACHE. Use
          None to disable caching. [optional]
    '''
    self.SetCache(cache)
    self._urllib = urllib2
    self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()
    self._input_encoding = input_encoding
    self.SetCredentials(username, password)

  def GetPublicTimeline(self, since_id=None):
    '''Fetch the sequnce of public Status message for all users.

    Args:
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      An sequence of Status instances, one for each message
    '''
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    url = 'http://twitter.com/statuses/public_timeline.json'
    json = self._FetchUrl(url,  parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewStatusFromJsonDict(x) for x in data]

  def GetFriendsTimeline(self,
                         user=None,
                         count=None,
                         since=None,
                         since_id=None):
    '''Fetch the sequence of Status messages for a user's friends

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If unspecified, the username and password
        must be set in the twitter.Api instance.  [Optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200. [Optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [Optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of Status instances, one for each message
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/statuses/friends_timeline/%s.json' % user
    else:
      url = 'http://twitter.com/statuses/friends_timeline.json'
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewStatusFromJsonDict(x) for x in data]

  def GetUserTimeline(self,
                      id=None,
                      user_id=None,
                      screen_name=None,
                      since_id=None,
                      max_id=None,
                      count=None,
                      page=None):
    '''Fetch the sequence of public Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      id:
        Specifies the ID or screen name of the user for whom to return
        the user_timeline. [optional]
      user_id:
        Specfies the ID of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid user ID
        is also a valid screen name. [optional]
      screen_name:
        Specfies the screen name of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid screen
        name is also a user ID. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200.  [optional]
      page:
         Specifies the page of results to retrieve. Note: there are
         pagination limits. [optional]

    Returns:
      A sequence of Status instances, one for each message up to count
    '''
    parameters = {}

    if id:
      url = 'http://twitter.com/statuses/user_timeline/%s.json' % id
    elif user_id:
      url = 'http://twitter.com/statuses/user_timeline.json?user_id=%d' % user_id
    elif screen_name:
      url = ('http://twitter.com/statuses/user_timeline.json?screen_name=%s' %
             screen_name)
    elif not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = 'http://twitter.com/statuses/user_timeline.json'

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if page:
      try:
        parameters['page'] = int(page)
      except:
        raise TwitterError("page must be an integer")

    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewStatusFromJsonDict(x) for x in data]

  def GetStatus(self, id):
    '''Returns a single status message.

    The twitter.Api instance must be authenticated if the status
    message is private.

    Args:
      id: The numerical ID of the status you're trying to retrieve.

    Returns:
      A Status instance representing that status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be a long integer")
    url = 'http://twitter.com/statuses/show/%s.json' % id
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewStatusFromJsonDict(data)

  def DestroyStatus(self, id):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and thee
    authenticating user must be the author of the specified status.

    Args:
      id: The numerical ID of the status you're trying to destroy.

    Returns:
      A Status instance representing the destroyed status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be a long integer")
    url = 'http://twitter.com/statuses/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewStatusFromJsonDict(data)

  def PostUpdate(self, status, in_reply_to_status_id=None):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  Must be less than or equal to
        140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
    Returns:
      A Status instance representing the message posted.
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = 'http://twitter.com/statuses/update.json'

    status_length = len(status)
    if status_length > CHARACTER_LIMIT:
      raise TwitterError("Text must be less than or equal to %d characters. "
                         "Was %d. Consider using PostUpdates." %
                         (CHARACTER_LIMIT, status_length))

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewStatusFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.
    Returns:
      A list of Status instances representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def GetReplies(self, since=None, since_id=None, page=None):
    '''Get a sequence of status messages representing the 20 most recent
    replies (status updates prefixed with @username) to the authenticating
    user.

    Args:
      page:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of Status instances, one for each reply to the user.
    '''
    url = 'http://twitter.com/statuses/replies.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewStatusFromJsonDict(x) for x in data]

  def GetFavorites(self,
                   user=None,
                   page=None):
    '''Fetch the sequence of Status messages a user has favorited.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If unspecified, the username and password
        must be set in the twitter.Api instance.  [Optional]
      page:
        Specifies the page of favorites to retrieve.  [Optional]

    Returns:
      A sequence of Status instances, one for each message
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/favorites/%s.json' % user
    else:
      url = 'http://twitter.com/favorites.json'
    parameters = {}
    if page is not None:
      try:
        if int(page) > 20:
          raise TwitterError("'page' may not be greater than 20")
      except ValueError:
        raise TwitterError("'page' must be an integer")
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewStatusFromJsonDict(x) for x in data]


  def GetFriends(self, user=None, page=None):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    Args:
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/statuses/friends/%s.json' % user
    else:
      url = 'http://twitter.com/statuses/friends.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewUserFromJsonDict(x) for x in data]

  def GetFollowers(self, page=None):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = 'http://twitter.com/statuses/followers.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewUserFromJsonDict(x) for x in data]

  def GetFeatured(self):
    '''Fetch the sequence of twitter.User instances featured on twitter.com

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances
    '''
    url = 'http://twitter.com/statuses/featured.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewUserFromJsonDict(x) for x in data]

  def GetUser(self, user):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user: The username or id of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show/%s.json' % user
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewUserFromJsonDict(data)

  def GetDirectMessages(self, since=None, since_id=None, page=None):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = 'http://twitter.com/direct_messages.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [NewDirectMessageFromJsonDict(x) for x in data]

  def PostDirectMessage(self, user, text):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      user: The ID or screen name of the recipient user.
      text: The message text to be posted.  Must be less than 140 characters.

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = 'http://twitter.com/direct_messages/new.json'
    data = {'text': text, 'user': user}
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewDirectMessageFromJsonDict(data)

  def DestroyDirectMessage(self, id):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url = 'http://twitter.com/direct_messages/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewDirectMessageFromJsonDict(data)

  def CreateFriendship(self, user):
    '''Befriends the user specified in the user parameter as the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user to befriend.
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url = 'http://twitter.com/friendships/create/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewUserFromJsonDict(data)

  def DestroyFriendship(self, user):
    '''Discontinues friendship with the user specified in the user parameter.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user  with whom to discontinue friendship.
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url = 'http://twitter.com/friendships/destroy/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewUserFromJsonDict(data)

  def ShowFriendships(self,
                      source_id=None,
                      source_screen_name=None,
                      target_id=None,
                      target_screen_name=None):
    '''Returns detailed information about the relationship between two users.

    Either source_id or source_screen_name must be supplied if the
    request is not unauthenticated.

    Args:
      source_id: The user_id of the subject user. [semi-optional, see above]
      source_screen_name: 
          The screen_name of the subject user. [semi-optional, see above]
      target_id: 
          The user_id of the target user. [one of target_id or 
          target_screen_name required]
      target_screen_name: 
          The screen_name of the target user. [one of target_id or 
          target_screen_name required]
    Returns:
      A Relationship instance.
    '''
    url = 'http://twitter.com/friendships/show.json'
    if not self._username and not source_id and not source_screen_name:
      raise TwitterError("Source must be specified if not authenticated.")
    parameters = {}
    if source_id:
      parameters['source_id'] = source_id
    if source_screen_name:
      parameters['source_screen_name'] = source_screen_name
    if target_id:
      parameters['target_id'] = target_id
    if target_screen_name:
      parameters['target_screen_name'] = target_screen_name
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewRelationshipFromJsonDict(data)


  def CreateFavorite(self, status):
    '''Favorites the status specified in the status parameter as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The Status instance to mark as a favorite.
    Returns:
      A Status instance representing the newly-marked favorite.
    '''
    url = 'http://twitter.com/favorites/create/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewStatusFromJsonDict(data)

  def DestroyFavorite(self, status):
    '''Un-favorites the status specified in the ID parameter as the authenticating user.
    Returns the un-favorited status in the requested format when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The Status to unmark as a favorite.
    Returns:
      A Status instance representing the newly-unmarked favorite.
    '''
    url = 'http://twitter.com/favorites/destroy/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewStatusFromJsonDict(data)

  def GetUserByEmail(self, email):
    '''Returns a single user by email address.

    Args:
      email: The email of the user to retrieve.
    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show.json?email=%s' % email
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewUserFromJsonDict(data)

  # some functions from lists API
  def GetUserLists(self, user=None, cursor=None):
    '''Fetch the sequence of twitter.List instances for a given user.

    Args:
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]
      cursor: previous/next_cursor from which to fetch, serves as a pagination 
      parameter. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A dictionary data with keys: 'previous_cursor', 'next_cursor', 'lists'
      data['lists'] is a sequence of twitter.Lists instances.
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/%s/lists.json' % user
    else:
      url = 'http://twitter.com/%s/lists.json' % self._username
    parameters = {}
    if cursor:
      parameters['cursor'] = cursor
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    data['lists'] = [NewListFromJsonDict(x) for x in data['lists']]
    return data

  def GetListMembers(self, list_slug, user=None, cursor=None):
    '''Fetch the sequence of twitter.User for a given

    Args:
      list_slug: list slug
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]
      cursor: previous/next_cursor from which to fetch, serves as a pagination
      parameter. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A dictionary data with keys: 'previous_cursor', 'next_cursor', 'users'
      data['users'] is a sequence of twitter.User instances.
    '''
    if not list_slug:
      raise TwitterError("List slug must be specified.")
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/%s/%s/members.json' % (user,list_slug)
    else:
      url = 'http://twitter.com/%s/%s/members.json' % (self._username,list_slug)
    parameters = {}
    if cursor:
      parameters['cursor'] = cursor 
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    data['users'] = [NewUserFromJsonDict(x) for x in data['users']]
    return data

  def GetList(self, list_slug, user=None):
    '''Fetch the List for a given user.

    Args:
      list_slug: slug of the list to fetch
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      The list information.
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = 'http://twitter.com/%s/lists/%s.json' % (user,list_slug)
    else:
      url = 'http://twitter.com/%s/lists/%s.json' % (self._username,list_slug)
    parameters = {}
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewListFromJsonDict(data)

  def Search(self,
             query,
             lang=None,
             rpp=None,
             page=None,
             since_id=None,
             geocode=None,
             show_user=None):
    '''Returns tweets that match a specified query.

    Args:
      query: The search query string, must be less than 140 characters
      lang:
        Restricts tweets to the given language, given by an ISO 639-1
        code. [Optional]
      rpp:
        The number of tweets to return per page, up to a max of 100. [Optional]
      page:
        The page number (starting at 1) to return, up to a max of
        roughly 1500 results (based on rpp * page. Note: there are
        pagination limits. [Optional]
      since_id:
        Returns tweets with status ids greater than the given id. [Optional]
      geocode:
        Returns tweets by users located within a given radius of the
        given latitude/longitude, where the user's location is taken
        from their Twitter profile. The parameter value is specified
        by "latitide,longitude,radius", where radius units must be
        specified as either "mi" (miles) or "km" (kilometers). Note
        that you cannot use the near operator via the API to geocode
        arbitrary locations; however you can use this geocode
        parameter to search near geocodes directly. [Optional]
      show_user:
        When true, prepends "<user>:" to the beginning of the
        tweet. This is useful for readers that do not display Atom's
        author field. The default is false. [Optional]
    Returns:
      A Results instance representing the search results
    '''
    url = 'http://search.twitter.com/search.json'

    parameters = {'q': query}
    if len(query) > 140:
      raise TwitterError('query must be <= 140 characters')
    if lang:
      parameters['lang'] = lang
    if rpp is not None:
      try:
        if int(rpp) > 100:
          raise TwitterError("'rpp' may not be greater than 100")
      except ValueError:
        raise TwitterError("'rpp' must be an integer")
      parameters['rpp'] = rpp
    if page:
      parameters['page'] = page
    if since_id:
      parameters['since_id'] = since_id
    if geocode:
      parameters['geocode'] = geocode
    if show_user:
      parameters['show_user'] = show_user
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewResultsFromJsonDict(data)

  def VerifyCredentials(self):
    '''Returns a twitter.User instance if the authenticating user is valid.

    Returns:
      A twitter.User instance representing that user if the
      credentials are valid, None otherwise.
    '''
    if not self._username:
      raise TwitterError("Api instance must first be given user credentials.")
    url = 'http://twitter.com/account/verify_credentials.json'
    try:
      json = self._FetchUrl(url, no_cache=True)
    except urllib2.HTTPError, http_error:
      if http_error.code == httplib.UNAUTHORIZED:
        return None
      else:
        raise http_error
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return NewUserFromJsonDict(data)

  def SetCredentials(self, username, password):
    '''Set the username and password for this instance

    Args:
      username: The twitter username.
      password: The twitter password.
    '''
    self._username = username
    self._password = password

  def ClearCredentials(self):
    '''Clear the username and password for this instance
    '''
    self._username = None
    self._password = None

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache: an instance that supports the same API as the twitter._FileCache
    '''
    if cache == DEFAULT_CACHE:
      self._cache = _FileCache()
    else:
      self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib: an instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout: time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent: a string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _AddAuthorizationHeader(self, username, password):
    if username and password:
      basic_auth = base64.encodestring('%s:%s' % (username, password))[:-1]
      self._request_headers['Authorization'] = 'Basic %s' % basic_auth

  def _RemoveAuthorizationHeader(self):
    if self._request_headers and 'Authorization' in self._request_headers:
      del self._request_headers['Authorization']

  def _GetOpener(self, url, username=None, password=None):
    if username and password:
      self._AddAuthorizationHeader(username, password)
      handler = self._urllib.HTTPBasicAuthHandler()
      (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
      handler.add_password(Api._API_REALM, netloc, username, password)
      opener = self._urllib.build_opener(handler)
    else:
      opener = self._urllib.build_opener()
    opener.addheaders = self._request_headers.items()
    return opener

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data: A python dict created from the Twitter json response
    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url: The URL to retrieve
      post_data:
        A dict of (str, unicode) key/value pairs.  If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added
        to the query string. [OPTIONAL]
      no_cache: If true, overrides the cache on the current request

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    # Add key/value parameters to the query string of the url
    url = self._BuildUrl(url, extra_params=extra_params)

    # Get a url opener that can handle basic auth
    opener = self._GetOpener(url, username=self._username, password=self._password)

    encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      url_data = opener.open(url, encoded_post_data).read()
      opener.close()
    else:
      # Unique keys are a combination of the url and the username
      if self._username:
        key = self._username + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        url_data = opener.open(url, encoded_post_data).read()
        opener.close()
        self._cache.Set(key, url_data)
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data


class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()

    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])
