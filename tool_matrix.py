import asyncio
import markdown
from typing import Optional

import nio

import tools

TIMEOUT = 30000         # milliseconds

class ToolSetMatrix(tools.ToolSetBasic):
    def __init__(self, config):
        super().__init__()

        self._config = config
        self._client = None         # nio client
        self._insecure = True       # Do not verify SSL
        self._default_room = self._config['room_id']
        self._timeout = TIMEOUT
        self._events = []
        self._event_loop = asyncio.get_event_loop()

        # Configuration options for the nio.AsyncClient
        client_config = nio.AsyncClientConfig(
            max_limit_exceeded = 0,
            max_timeouts = 0,
            store_sync_tokens = True,
            encryption_enabled = True,
        )
        # Initialize the matrix client based on configuration
        self._client = nio.AsyncClient(
            self._config['homeserver'],
            self._config['user_id'],
            device_id = self._config['device_id'],
            store_path = 'store',
            config = client_config,
            ssl = not self._insecure,
            proxy = None,
        )
        self._client.add_event_callback(self._event_callback, nio.RoomMessageText)

        self._client.restore_login(
            user_id = self._config['user_id'],
            device_id = self._config['device_id'],
            access_token = self._config['access_token'],
        )

    def tools(self):
        return [
('''send_message(message: str):
    """
    Sends a message to the users. This is the only way to communicate with users.
    Supports Markdown for formatting.
    Example: send_message(message='**Hello**! How are you today?')
    """
''', self._send_message),
        ]

    def _send_message(self, message: str):
        # "Logged in as @alice:example.org device id: RANDOMDID"
        # If you made a new room and haven't joined as that user, you can use
        # await self._client.join("your-room-id")

        self._sync()
        room_id = self._event_loop.run_until_complete(self._map_roominfo_to_roomid(self._default_room))

        html = markdown.markdown(message, extensions=['tables', 'extra', 'sane_lists'])
        resp = self._event_loop.run_until_complete(self._client.room_send(
            # Watch out! If you join an old room you'll see lots of old messages
            room_id = room_id,
            message_type = 'm.room.message',
            content = {
                'msgtype': 'm.text',
                'format': 'org.matrix.custom.html',
                'formatted_body': html,
                'body': html,
            },
            ignore_unverified_devices = True,
        ))

    def get_events(self):
        self._sync()
        events = self._events
        self._events = []

        r = []
        for e in events:
            if e[1].source['type'] != 'm.room.message':
                continue
            if e[1].sender == self._config['user_id']:
                continue        # Skip events from self
            r.append({
                'type': e[1].source['type'],
                'sender': e[1].source['sender'],
                'room': e[0].display_name,
                'msgtype': e[1].source['content']['msgtype'],
                'body': e[1].source['content']['body'],
                'origin_server_ts': e[1].source['origin_server_ts'],
            })
        return r

    async def _event_callback(self, room: nio.MatrixRoom, event: nio.RoomMessageText) -> None:
        self._events.append((room, event))

    def _sync(self):
        self._event_loop.run_until_complete(self._client.sync(timeout=self._timeout, full_state=True))

    async def _map_roominfo_to_roomid(self, info: str) -> str:
        """Attempt to convert room info to room_id.

        Arguments:
        ---------
        info : str
            can be a canonical alias in the form of '#someRoomAlias:example.com'
            can be a canonical room_id in the form of '!someRoomId:example.com'
            can be a short alias in the form of 'someRoomAlias'
            can be a short alias in the form of '#someRoomAlias'
            can be a short room id in the form of '!someRoomId'

        Return corresponding full room_id (!id:sample.com) or or raises exception.

        """
        ri = info.strip()
        ri = ri.replace(r'\!', '!')  # remove possible escape
        if (
            ri in (None, '', '!', '#')
            or ri[0] == ':'
            or ri.count(':') > 1
            or ri[0] == '@'
            or '#' in ri[1:]
            or any(elem in ri for elem in '[]{} ')  # does it contain bad chars?
            or (
                ri[0]!='!' and ri[0]!='#' and ':' in ri
            )  # alias:sample.com
        ):
            err = (
                f'Invalid room specification. "{info}" ({ri}) is neither '
                'a valid room id nor a valid room alias.'
            )
            raise Exception(err)
        if ri[0]!='!':
            # 'someRoomAlias' or '#someRoomAlias' or '#someRoomAlias:sample.com'
            if ':' not in ri:  # 'someRoomAlias' or '#someRoomAlias'
                ri = self._short_room_alias_to_room_alias(ri)
            ri = await self._map_roomalias_to_roomid(ri)
            return ri
        if ':' not in ri:
            # '!someRoomId'
            ri += ':' + self._default_homeserver()
        return ri

    async def _map_roomalias_to_roomid(self, alias) -> str:
        """Attempt to convert room alias to room_id.

        Arguments:
        ---------
        alias : can be an alias in the form of '#someRoomAlias:example.com'
            can also be a room_id in the form of '!someRoomId:example.com'

        room_id : room from configuration
    
        If an alias try to get the corresponding room_id.
        If anything fails it returns the original input.

        Return corresponding room_id or on failure the original alias.

        """
        ret = alias
        if self._is_room_alias(alias):
            resp = await self._client.room_resolve_alias(alias)
            if isinstance(resp, nio.RoomResolveAliasError):
                print(
                    f'room_resolve_alias for alias {alias} failed with '
                    f'{self._privacy_filter(str(resp))}. '
                    f'Trying operation with input {alias} anyway. Might fail.'
                )
            else:
                ret = resp.room_id
        return ret

    def _is_room_alias(self, room_id: str) -> bool:
        """Determine if room identifier is a room alias.

        Room aliases are of syntax: #somealias:someserver
        This is not an exhaustive check!

        """
        return (
            room_id
            and len(room_id) > 3
            and (room_id[0] == '#')
            and ('#' not in room_id[1:])
            and (':' in room_id)
            and room_id.count(':') == 1
            and (' ' not in room_id)
            and not any(elem in room_id for elem in '[]{} ')  # contains bad chars?
        )

    def _short_room_alias_to_room_alias(self, short_room_alias: str):
        """Convert 'SomeRoomAlias' to ''#SomeToomAlias:matrix.example.com'.
        Converts short canonical local room alias to full room alias.
        """
        if short_room_alias in (None, ''):
            err = 'Invalid room alias. Alias is none or empty.'
            raise Exception(err)
        if short_room_alias[0] == '#':
            ret = short_room_alias + ':' + self._default_homeserver()
        else:
            ret = '#' + short_room_alias + ':' + self._default_homeserver()
        return ret

    def _default_homeserver(self):
        """Get the default homeserver (domain) from the configuration.
        Use the user_id, not the room_id. The room_id could be on a
        different server owned by someone else. user_id makes more sense.
        """
        user = self._config['user_id']  # who am i
        homeserver = user.split(':',1)[1]
        return homeserver  # matrix.example.com

    def _privacy_filter(self, dirty: str) -> str:
        """Remove private info from string"""
        return dirty.replace(self._config['access_token'], '***')


# Tests
if __name__ == '__main__':
    import json
    import time
    CONFIG_FILE = 'config.json'
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    tools_matrix = tool_matrix.ToolSetMatrix(config)
    print('Listening to Matrix events...')
    while True:
        matrix_events = tools_matrix.get_events()
        if matrix_events:
            print(matrix_events)
        time.sleep(1)
