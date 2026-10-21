import json


class RedisGroupIdentityStore:
    """Stores connection identities beside the ephemeral Redis room group."""

    def __init__(self, channel_layer, group_name):
        try:
            index = channel_layer.consistent_hash(group_name)
            self.redis = channel_layer.connection(index)
            group_key = channel_layer._group_key(group_name)
        except AttributeError as exc:
            raise RuntimeError(
                "Collaboration identities require the configured RedisChannelLayer"
            ) from exc

        suffix = b":identities" if isinstance(group_key, bytes) else ":identities"
        self.identity_key = group_key + suffix
        self.expiry = channel_layer.group_expiry

    async def set(self, channel_name, token, name):
        value = json.dumps({"token": token, "name": name}, ensure_ascii=False)
        await self.redis.hset(self.identity_key, channel_name, value)
        await self.redis.expire(self.identity_key, self.expiry)

    async def names(self, members):
        if not members:
            return {}

        values = await self.redis.hmget(self.identity_key, members)
        result = {}
        for member, value in zip(members, values):
            if value is None:
                continue
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            try:
                identity = json.loads(value)
            except (TypeError, ValueError):
                continue
            name = identity.get("name")
            if isinstance(name, str):
                result[member] = name
        return result

    async def delete(self, channel_name):
        await self.redis.hdel(self.identity_key, channel_name)
