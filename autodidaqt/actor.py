from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio

from autodidaqt.state import ActorState

if TYPE_CHECKING:
    from autodidaqt import AutodiDAQt

__all__ = ("Actor", "EchoActor", "MessagingActor")


class StopException(Exception):
    pass


class Actor:
    panel_cls = None

    def __init__(self, app: AutodiDAQt):
        self.app = app
        self.messages = None

    async def prepare(self):
        self.messages = asyncio.Queue()

    async def run(self):
        raise NotImplementedError

    async def shutdown(self):
        pass

    def collect_state(self) -> ActorState:
        return ActorState()

    def receive_state(self, state: ActorState):
        pass

    def collect_remote_state(self):
        return None

    def collect_extra_wire_types(self):
        return {}


class MessagingActor(Actor):
    async def run(self):
        """
        Actions that should be run repeatedly should be put in run_step.
        Only overwrite run (with a super().run() call included) for tasks done once.
        This probably never happens since these tasks should just be included in an actors prepare function.
        """
        try:
            while True:
                await self.read_messages()
                await self.run_step()
        except StopException:
            return

    async def handle_user_message(self, message):
        pass

    async def handle_message(self, message):
        from autodidaqt_common.remote.command import RequestShutdown

        if isinstance(message, RequestShutdown):
            await self.shutdown()
            await message.respond_did_shutdown(self.app)
            raise StopException()

        await self.handle_user_message(message)

    async def read_messages(self):
        try:
            while True:
                message = self.messages.get_nowait()
                self.messages.task_done()
                await self.handle_message(message)
        except asyncio.QueueEmpty:
            pass

    async def run_step(self):
        """
        Overwrite this function to add repeated tasks during runtime.
        """
        pass


class EchoActor(Actor):
    async def handle_user_message(self, message):
        print(message)
