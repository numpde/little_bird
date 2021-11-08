# RA, 2021-11-08

#

import contextlib
import http.client
import requests
import datetime

from typing import List, Tuple, Dict, Iterable

import requests_oauthlib

TWEET_MAX_LEN = 280


class TwitterError(BaseException):
    pass


class DuplicateTweetError(TwitterError):
    pass


def parse(response: requests.Response) -> Tuple[requests.Response, Dict]:
    """
    Attempt to JSON-deserialize the content of a request response.

    If it appears to be an error reported by Twitter
    then `TwitterError` is raised.

    Args:
        response: Request response returned by `get` and such.

    Returns:
        (response, content)

    Raises:
        `Exception` if the content could not be parsed as a `dict`.
        `TwitterError` as above.
    """

    try:
        content = response.json()
        assert isinstance(content, dict)
    except:
        raise Exception(f"Cannot parse the response. Status {response.status_code}: {response.text}.")

    try:
        raise TwitterError(content['errors'])
    except KeyError:
        pass

    return (response, content)


def strftime(timestamp):
    t = datetime.datetime.fromtimestamp(timestamp).astimezone(tz=datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


class LittleBird:
    def __init__(self, auth_params: dict):
        """
        Args:
            auth_params: is a dict containing
                'consumer_key', 'consumer_secret', 'access_token', 'access_token_secret'
                (these are converted to the corresponding parameters for `OAuth1Session`)
                and any other kwargs for `OAuth1Session` (from requests_oauthlib).
        """

        # Twitter terminology -> OAuth terminology
        rename = {
            # App authentication
            'consumer_key': "client_key",
            'consumer_secret': "client_secret",
            # App's access to a user account
            'access_token': "resource_owner_key",
            'access_token_secret': "resource_owner_secret",
        }

        for k in rename:
            if not auth_params[k]:
                raise ValueError(f"Nontrivial value expected for '{k}'.")

        # Rename keys in `oauth_params`
        self.oauth_params = {
            rename.get(k, k): v
            for (k, v) in auth_params.items()
        }

        allowed_keys = set(requests_oauthlib.OAuth1Session.__init__.__code__.co_varnames) - {'self', 'kwargs'}

        assert set(self.oauth_params.keys()).issubset(allowed_keys), \
            f"Unexpected arguments supplied in `oauth_params`."

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @contextlib.contextmanager
    def oauth(self) -> requests_oauthlib.OAuth1Session:
        with requests_oauthlib.OAuth1Session(**self.oauth_params) as oauth:
            assert oauth.authorized
            yield oauth

    def get_tweets_by_id(self, ids: List[str]):
        """
        Args:
            ids: Tweet ids as strings, e.g. ['20', '21'].

        Returns:
            Tweets in the format [{'id': ..., 'text': ...}, ...].

        Raises:
            requests.exceptions.ConnectionError
            ValueError: If `ids` is clearly malformed.
            TwitterError: Generally if the response is in form {'errors': ...}.
        """

        if (not ids) or (not isinstance(ids, list)) or (not all(ids)):
            raise ValueError("A list of tweet ids is required.")

        with self.oauth() as oauth:
            url = "https://api.twitter.com/2/tweets"
            (response, content) = parse(oauth.get(url, params={'ids': ",".join(ids)}))

            if response.status_code not in {200, 400}:
                raise Exception(f"Status {response.status_code}: {response.text}.")

            return content['data']

    def tweet(self, text: str) -> dict:
        """
        Tweet something.

        In case of a duplicate tweet, `DuplicateTweetError` is raised.

        Args:
            text: Content of the tweet.

        Returns:
            Typically a dict like {'id': '1457709521896357893', 'text': 'Hello, world!'}.
        """

        if not isinstance(text, str):
            raise TypeError(f"Tweet should be a string.")
        else:
            text = text.strip()

        if not text:
            raise ValueError(f"Tweet should not be empty.")

        if len(text) > TWEET_MAX_LEN:
            raise OverflowError(f"The intended tweet is too long (max: {TWEET_MAX_LEN}).")

        with self.oauth() as oauth:
            url = "https://api.twitter.com/2/tweets"
            payload = {'text': text}
            (response, content) = parse(oauth.post(url, json=payload))

            if response.status_code == http.client.CREATED:
                # Tweet created; return the 'data' of the form
                # {'id': '1457709521896357893', 'text': 'Hello, world!'}
                return content['data']

            if response.status_code == http.client.FORBIDDEN:
                if content.get('detail', "").endswith("duplicate content."):
                    raise DuplicateTweetError(content)
                else:
                    raise TwitterError(content)

            # Anomalous situation
            raise Exception(f"Status {response.status_code}: {content}.")

    def untweet(self, id: str) -> dict:
        """
        Delete a tweet.
        No error is raised if it is already deleted.

        Args:
            id: The id of the tweet.

        Returns:
            Typically {'deleted': True}.
        """

        with self.oauth() as oauth:
            url = f"https://api.twitter.com/2/tweets/{id}"
            (response, content) = parse(oauth.delete(url))

            if response.status_code == http.client.FORBIDDEN:
                raise TwitterError(content)

            if response.status_code == http.client.OK:
                return content['data']

            # Anomalous situation
            raise Exception(f"Status {response.status_code}: {content}.")

    def users_by_username(self, usernames: List[str]):
        """
        Retrieve basic user info from their username(s)
        such as {'id': '12', 'name': 'jack⚡️', 'username': 'jack'}.

        Main purpose is to map username to user id.

        Args:
            usernames: list of usernames, e.g. ['jack', 'elonmusk'].

        Returns:
            List like [{'id': ..., 'name': ..., 'username': ...}, ...].
        """

        with self.oauth() as oauth:
            url = "https://api.twitter.com/2/users/by"
            params = {'usernames': usernames}
            (response, content) = parse(oauth.get(url, params=params))

            if response.status_code == http.client.OK:
                return content['data']

        # Anomalous situation
        raise Exception(f"Status {response.status_code}: {content}.")

    def tweets_by_user_id(self, user_id: str, start_time=None, end_time=None) -> Iterable[Dict]:
        """
        Retrieve all tweets by a given user.

        Args:
            user_id: user id (such as '15506669' for @JeffBezos).
            start_time: timestamp.
            end_time: timestamp.

        Yields:
            Tweets in reverse chronological order.
        """

        max_results_per_page = 50

        with self.oauth() as oauth:
            url = f"https://api.twitter.com/2/users/{user_id}/tweets"

            # https://developer.twitter.com/en/docs/twitter-api/tweets/timelines/api-reference/get-users-id-tweets
            params = {
                'tweet.fields': "created_at",
                'max_results': max_results_per_page,
            }

            if start_time:
                params.update({'start_time': strftime(start_time)})

            if end_time:
                params.update({'end_time': strftime(end_time)})

            # Pagination loop
            while True:
                (response, content) = parse(oauth.get(url, params=params))

                meta = content['meta']
                data = content['data']

                yield from data

                if 'next_token' in meta:
                    params.update({'pagination_token': meta.get('next_token')})
                else:
                    break
