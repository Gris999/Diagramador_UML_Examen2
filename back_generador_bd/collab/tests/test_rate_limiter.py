from unittest import mock

from django.test import SimpleTestCase

from collab.limits import InMemoryRateLimiter, RedisRateLimiter


class RateLimiterContract:
    """Lo que debe cumplir cualquier adaptador del puerto RateLimiter: a lo más `limit` pedidos por clave en cada ventana de tiempo."""

    def make_limiter(self):
        raise NotImplementedError

    def at(self, seconds):
        raise NotImplementedError

    def test_it_allows_up_to_the_limit_and_then_refuses(self):
        limiter = self.make_limiter()

        with self.at(1000):
            resultados = [limiter.allow("persona", 3, 60) for _ in range(5)]

        self.assertEqual(resultados, [True, True, True, False, False])

    def test_each_key_has_its_own_count(self):
        limiter = self.make_limiter()

        with self.at(1000):
            for _ in range(3):
                limiter.allow("ana", 3, 60)

            self.assertFalse(limiter.allow("ana", 3, 60))
            self.assertTrue(limiter.allow("beto", 3, 60))

    def test_a_new_window_starts_counting_again(self):
        limiter = self.make_limiter()
        with self.at(1000):
            for _ in range(4):
                limiter.allow("persona", 3, 60)

        with self.at(1075):
            self.assertTrue(limiter.allow("persona", 3, 60))

    def test_a_refused_request_is_reported_to_whoever_asked_but_does_not_hide_later_windows(self):
        limiter = self.make_limiter()
        with self.at(1000):
            self.assertTrue(limiter.allow("persona", 1, 60))
            self.assertFalse(limiter.allow("persona", 1, 60))

        with self.at(1200):
            self.assertTrue(limiter.allow("persona", 1, 60))


class InMemoryRateLimiterTests(RateLimiterContract, SimpleTestCase):
    def setUp(self):
        InMemoryRateLimiter.reset()

    def make_limiter(self):
        return InMemoryRateLimiter()

    def at(self, seconds):
        return mock.patch("collab.limits.time.time", return_value=float(seconds))


class FakeRedis:
    """Lo mínimo de un cliente de Redis que usa RedisRateLimiter: INCR y EXPIRE (la expiración se anota, no corre sola)."""

    def __init__(self):
        self.counts = {}
        self.expirations = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds


class RedisRateLimiterTests(RateLimiterContract, SimpleTestCase):
    def make_limiter(self):
        self.client = FakeRedis()
        return RedisRateLimiter(self.client)

    def at(self, seconds):
        return mock.patch("collab.limits.time.time", return_value=float(seconds))

    def test_each_counter_expires_on_its_own_so_redis_does_not_fill_up(self):
        limiter = self.make_limiter()

        with self.at(1000):
            limiter.allow("persona", 3, 60)

        self.assertEqual(len(self.client.expirations), 1)
        self.assertGreaterEqual(list(self.client.expirations.values())[0], 60)
