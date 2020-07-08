# TrackerCog

The TrackerCog class is designed to simplify the task of regularly checking
HTTP resources for updates, and notify channels of such updates.

### Basics

This class only has two compulsory methods that should be overridden, which
are the do_work() coroutine method and the topic() property. By default,
do_work() will be fired at regular intervals, unless you make themethod return
`False`.

You may override update_interval_secs() to change the interval at which
do_work() is repeated.

For convenience, the cog implementing the publish/subscribe mechanism for
channels can be accessed with the `pubsubcog` attribute, which allows you to
push updates into subscribed channels using the `pubsubcog.push_to_topic()`
awaitable.

One approach to using this class is to create a mixin with a do_work() method
that defines the generic tasks relevant to a platform (e.g. Twitch).
Then, you subclass the mixin, followed by TrackerCog, to define individual
cases on the platform.

This approach allows you to spend some time defining procedures for each
platform using mixins (as abstractly as you like!), so that individual cases
on each platform will only have to provide some 'configuration' params.

### Example

```python
    class StalkJimmyBean(TwitchMixin, TrackerCog):
        """A cog that maps multiple channels to one topic 'jimbean'
        In this case, we are stalking someone with two accounts, named
        'JimmyBean' and 'JimBean123'
        """
        @property
        def topic(self):
            # Overwrite property required by TrackerCog
            return 'jimbean'

        @property
        def target_usernames(self):
            # Overwrite property required by TwitchMixin
            return ['JimmyBean', 'JimBean123']

    class StalkEsports(TwitchMixin, TrackerCog):
        """Another case, this time for some esports channel"""
        @property
        def topic(self): return 'esports'
        @property
        def target_usernames(self): return ['esportschannel']

    class TwitchMixin:
        """A mixin that defines some common action on the Twitch platform
        In this case, we want to get the stream of some users, which will be
        defined via the target_usernames() property.
        do_work() will ping the endpoint for updates, and inform subscribed
        channels using pubsubcog.push_to_topic()
        """
        @property
        def target_usernames(self):
            """Abstract, expects a list of usernames.
            To be implemented by the cog that controls the
            username-to-topic mapping.
            """
            raise NotImplementedError

        @property
        def update_interval_secs(self):
            return 1/10  # repeat every 0.1 sec (bad idea! but doable)

        async def call_endpoint(self, users):
            streams = []
            for user in users:
                resp = await self.fetch(...)  # TrackerCog.fetch
                # json() method is awaited as a quirk from aiohttp, the API
                # underlying TrackerCog.fetch()
                streams.append(await resp.json())
            return streams

        async def do_work():
            streams = await self.call_endpoint(self.users)
            # pubsubcog.push_to_topic() accepts replies as dicts
            # defining two keys, 'content': str and 'embed': discord.Embed
            replies = [dict(content='Stream up!',
                            embed=TwitchStream.to_embed(json_data))
                       for json_data in streams]
            self.pubsubcog.push_to_topic(self.topic, replies)
            return True

    class TwitchStream:
        """Wrapper over Twitch API response, with embed conversion method"""
        @staticmethod
        def to_embed(stream_json_data):
            return discord.Embed(...)
```

### Integration with other components
You can access the database by subclassing `cogs.mixins.DatabaseCogMixin`.
This gives you SQL access to the database using methods like `db_execute()`.

You can access other loaded cogs using the bound method
`TrackerCog.bot.get_cog('somecogname')`.

`TrackerCog` itself is a subclass of `discord.ext.commands.Cog`.
