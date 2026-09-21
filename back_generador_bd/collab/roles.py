class RedisGroupRoleStore:
    """Uses the Redis channel-group membership as ephemeral role state."""

    _LEAVE_SCRIPT = """
        local removed = redis.call('ZREM', KEYS[1], ARGV[1])
        local members = redis.call('ZRANGE', KEYS[1], 0, -1)
        table.insert(members, 1, removed)
        return members
    """

    _REMOVE_BY_HOST_SCRIPT = """
        local host = redis.call('ZRANGE', KEYS[1], 0, 0)[1]
        if not host or host ~= ARGV[1] or ARGV[1] == ARGV[2] then
            return {0}
        end
        if not redis.call('ZSCORE', KEYS[1], ARGV[2]) then
            return {0}
        end
        redis.call('ZREM', KEYS[1], ARGV[2])
        local members = redis.call('ZRANGE', KEYS[1], 0, -1)
        table.insert(members, 1, 1)
        return members
    """

    def __init__(self, channel_layer, group_name):
        self.channel_layer = channel_layer
        self.group_name = group_name

        try:
            index = channel_layer.consistent_hash(group_name)
            self.redis = channel_layer.connection(index)
            self.group_key = channel_layer._group_key(group_name)
        except AttributeError as exc:
            raise RuntimeError(
                "Collaboration roles require the configured RedisChannelLayer"
            ) from exc

    async def join(self, channel_name):
        await self.channel_layer.group_add(self.group_name, channel_name)
        return await self.members()

    async def members(self):
        values = await self.redis.zrange(self.group_key, 0, -1)
        return self._decode_members(values)

    async def leave(self, channel_name):
        result = await self.redis.eval(
            self._LEAVE_SCRIPT,
            1,
            self.group_key,
            channel_name,
        )
        return bool(result[0]), self._decode_members(result[1:])

    async def remove_by_host(self, requester, target):
        result = await self.redis.eval(
            self._REMOVE_BY_HOST_SCRIPT,
            1,
            self.group_key,
            requester,
            target,
        )
        return bool(result[0]), self._decode_members(result[1:])

    @staticmethod
    def _decode_members(values):
        return [
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in values
        ]
