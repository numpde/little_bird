# RA, 2021-11-08

from unittest import TestCase

import os
import datetime

from uuid import uuid4 as unique_id

from dotenv import load_dotenv

from little_bird import LittleBird
from little_bird import TwitterError, DuplicateTweetError


def get_valid_auth_params():
    load_dotenv()
    auth_params = {
        'consumer_key': os.environ.get("CONSUMER_KEY"),
        'consumer_secret': os.environ.get("CONSUMER_SECRET"),
        'access_token': os.environ.get("ACCESS_TOKEN"),
        'access_token_secret': os.environ.get("ACCESS_TOKEN_SECRET"),
    }
    return auth_params


class TestLittleBird(TestCase):
    def test_constructor(self):
        LittleBird(auth_params=get_valid_auth_params())

    def test_constructor_raises_on_missing_auth(self):
        auth_params = get_valid_auth_params()

        for x in auth_params:
            # Missing key
            with self.assertRaises(KeyError):
                LittleBird(auth_params={k: v for (k, v) in auth_params.items() if (k != x)})

            # Missing value
            with self.assertRaises(ValueError):
                LittleBird(auth_params={k: (v if (k != x) else "") for (k, v) in auth_params.items()})

    def test_get_tweets_by_id(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        tweets = lb.get_tweets_by_id(ids=['20', '200'])

        expected = [
            {'id': "20", 'text': "just setting up my twttr"},
            {'id': "200", 'text': "trying to get odeo thoughts down"},
        ]

        self.assertEqual(tweets, expected)

    def test_get_tweets_by_id_fails_on_bogus_ids(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        with self.assertRaises(ValueError):
            lb.get_tweets_by_id(ids=[''])  # Unspecified id

        with self.assertRaises(TwitterError):
            lb.get_tweets_by_id(ids=['1'])  # No such tweet

    def test_tweet_raises_if_malformed(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        with self.assertRaises(OverflowError):
            lb.tweet("she said that " * 100)

        with self.assertRaises(TypeError):
            lb.tweet(43)

        with self.assertRaises(ValueError):
            lb.tweet(" ")

    def test_tweet_duplicate(self):
        lb = LittleBird(auth_params=get_valid_auth_params())
        text = str(unique_id())

        tweet_id = lb.tweet(text).pop('id')

        # Successful tweet(...) returns
        # {'id': '1457709521896357893', 'text': 'Hello, world!'}

        with self.assertRaises(DuplicateTweetError):
            lb.tweet(text)

        lb.untweet(tweet_id)

    def test_delete_again(self):
        lb = LittleBird(auth_params=get_valid_auth_params())
        self.assertDictEqual({'deleted': True}, lb.untweet('3'))

    def test_delete_invalid(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        with self.assertRaises(TwitterError):
            lb.untweet('-1')

        with self.assertRaises(TwitterError):
            lb.untweet('20')

    def test_tweet_and_delete(self):
        lb = LittleBird(auth_params=get_valid_auth_params())
        tweet_id = lb.tweet(str(unique_id())).pop('id')
        self.assertDictEqual({'deleted': True}, lb.untweet(tweet_id))

    def test_users_by_username(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        [userdata] = lb.users_by_username(usernames=["jack"])
        self.assertEqual(userdata['username'], "jack")
        self.assertEqual(userdata['id'], "12")

        [userdata] = lb.users_by_username(usernames=["JeffBezos"])
        self.assertEqual("JeffBezos", userdata['username'])
        self.assertEqual('15506669', userdata['id'])

    def test_tweets_by_user_id(self):
        lb = LittleBird(auth_params=get_valid_auth_params())

        (username, user_id) = ("JeffBezos", '15506669')
        # user_id = lb.users_by_username(usernames=[username]).pop().get('id')

        end_time = datetime.datetime.fromisoformat("2021-01-01T00:00:00+00:00").timestamp()

        tweets = list(lb.tweets_by_user_id(user_id=user_id, end_time=end_time))

        self.assertEqual(len(list(tweets)), 240)
