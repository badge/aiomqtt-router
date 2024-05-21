import asyncio
from collections.abc import Awaitable, Callable

import aiomqtt
from aiomqtt.types import SubscribeTopic
from paho.mqtt.properties import Properties
from paho.mqtt.subscribeoptions import SubscribeOptions


from typing import Any, TypeAlias, TypedDict

__all__ = ["AiomqttRouter"]


MessageHandler: TypeAlias = Callable[[aiomqtt.Message], None]
AsyncMessageHandler: TypeAlias = Callable[[aiomqtt.Message], Awaitable[None]]


class SubscibeArgs(TypedDict):

    qos: int
    options: SubscribeOptions | None
    properties: Properties | None
    args: Any
    timeout: float | None
    kwargs: Any


class TopicHandler:

    def __init__(
        self,
        handler: MessageHandler | AsyncMessageHandler,
        subscribe_args: SubscibeArgs,
    ):
        self.queue: asyncio.Queue[aiomqtt.Message] = asyncio.Queue()
        self.consumer = self.create_consumer(handler)
        self.subscribe_args = subscribe_args

    def create_consumer(self, handler: MessageHandler | AsyncMessageHandler):
        if asyncio.iscoroutinefunction(handler):

            async def consumer():
                while True:
                    message = await self.queue.get()
                    await handler(message)

        else:

            async def consumer():
                while True:
                    message = await self.queue.get()
                    handler(message)

        return consumer

    def __call__(self):
        return self.consumer()


class AiomqttRouter:

    def __init__(self):
        self._handlers: dict[SubscribeTopic, TopicHandler] = {}

    def subscribe(
        self,
        topic: SubscribeTopic,
        qos: int = 0,
        options: SubscribeOptions | None = None,
        properties: Properties | None = None,
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ):
        """Subscribe to a topic or wildcard.

        Args:
            topic: The topic or wildcard to subscribe to.
            qos: The requested QoS level for the subscription.
            options: (MQTT v5.0 only) Optional paho-mqtt subscription options.
            properties: (MQTT v5.0 only) Optional paho-mqtt properties.
            *args: Additional positional arguments to pass to paho-mqtt's subscribe
                method.
            timeout: The maximum time in seconds to wait for the subscription to
                complete. Use ``math.inf`` to wait indefinitely.
            **kwargs: Additional keyword arguments to pass to paho-mqtt's subscribe
                method.
        """
        subscribe_args = SubscibeArgs(
            qos=qos,
            options=options,
            properties=properties,
            args=args,
            timeout=timeout,
            kwargs=kwargs,
        )

        def outer(handler: MessageHandler | AsyncMessageHandler):
            self._handlers[topic] = TopicHandler(handler, subscribe_args)
            return handler

        return outer

    async def distributor(self, client: aiomqtt.Client):
        async for message in client.messages:
            for topic, handler in self._handlers.items():
                if message.topic.matches(topic):
                    handler.queue.put_nowait(message)

    async def __call__(self, client: aiomqtt.Client):
        for topic, handler in self._handlers.items():
            await client.subscribe(
                topic,
                handler.subscribe_args["qos"],
                handler.subscribe_args["options"],
                handler.subscribe_args["properties"],
                *handler.subscribe_args["args"],
                timeout=handler.subscribe_args["timeout"],
                **handler.subscribe_args["kwargs"],
            )

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.distributor(client=client))
            for handler in self._handlers.values():
                tg.create_task(handler())
