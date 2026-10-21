from datetime import datetime, timezone


class InMemoryRoleStore:
    rooms = {}

    def __init__(self, channel_layer, group_name):
        self.channel_layer = channel_layer
        self.group_name = group_name

    async def join(self, channel_name):
        await self.channel_layer.group_add(self.group_name, channel_name)
        members = self.rooms.setdefault(self.group_name, [])
        if channel_name not in members:
            members.append(channel_name)
        return list(members)

    async def members(self):
        return list(self.rooms.get(self.group_name, []))

    async def leave(self, channel_name):
        await self.channel_layer.group_discard(self.group_name, channel_name)
        members = self.rooms.get(self.group_name, [])
        if channel_name not in members:
            return False, list(members)
        members.remove(channel_name)
        if not members:
            self.rooms.pop(self.group_name, None)
        return True, list(members)

    async def remove_by_host(self, requester, target):
        members = self.rooms.get(self.group_name, [])
        if not members or members[0] != requester or target == requester:
            return False, list(members)
        if target not in members:
            return False, list(members)
        members.remove(target)
        await self.channel_layer.group_discard(self.group_name, target)
        return True, list(members)


class InMemoryIdentityStore:
    rooms = {}

    def __init__(self, _channel_layer, group_name):
        self.group_name = group_name

    async def set(self, channel_name, token, name):
        identities = self.rooms.setdefault(self.group_name, {})
        identities[channel_name] = {"token": token, "name": name}

    async def names(self, members):
        identities = self.rooms.get(self.group_name, {})
        return {
            member: identities[member]["name"]
            for member in members
            if member in identities
        }

    async def delete(self, channel_name):
        identities = self.rooms.get(self.group_name, {})
        identities.pop(channel_name, None)
        if not identities:
            self.rooms.pop(self.group_name, None)


class InMemoryActivityStore:
    participants = {}
    events = []

    async def identify(self, room, token, name):
        actor_id = self.participants.get((room, token), {}).get("id")
        if actor_id is None:
            actor_id = len(self.participants) + 1
        self.participants[(room, token)] = {"id": actor_id, "name": name}
        return actor_id

    async def record(
        self,
        *,
        room,
        actor_id,
        actor_name,
        event_type,
        target_id,
        summary,
        data,
    ):
        event = {
            "id": len(self.events) + 1,
            "room": room,
            "actor": actor_id,
            "actor_name": actor_name,
            "actor_kind": "user",
            "type": event_type,
            "target_id": target_id,
            "summary": summary,
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        return event


class FailingActivityStore(InMemoryActivityStore):
    async def record(self, **kwargs):
        raise RuntimeError("database unavailable")


def reset_stores():
    InMemoryRoleStore.rooms.clear()
    InMemoryIdentityStore.rooms.clear()
    InMemoryActivityStore.participants.clear()
    InMemoryActivityStore.events.clear()
