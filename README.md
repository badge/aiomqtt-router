# aiomqtt-router

An async router for MQTT topics with aiomqtt.

`aiomqtt-router` makes subscribing to multiple MQTT topics with
[aiomqtt](https://sbtinstruments.github.io/aiomqtt/index.html) much more straightforward
and tidier than it otherwise would be. Here's an example
[from the aiomqtt docs](https://sbtinstruments.github.io/aiomqtt/migration-guide-v2.html#changes-to-the-message-queue)
**without** aiomqtt-router:


```python
import asyncio
import aiomqtt


async def temperature_consumer():
    while True:
        message = await temperature_queue.get()
        print(f"[temperature/#] {message.payload}")


async def humidity_consumer():
    while True:
        message = await humidity_queue.get()
        print(f"[humidity/#] {message.payload}")


temperature_queue = asyncio.Queue()
humidity_queue = asyncio.Queue()


async def distributor(client):
    # Sort messages into the appropriate queues
    async for message in client.messages:
        if message.topic.matches("temperature/#"):
            temperature_queue.put_nowait(message)
        elif message.topic.matches("humidity/#"):
            humidity_queue.put_nowait(message)


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await client.subscribe("temperature/#")
        await client.subscribe("humidity/#")
        # Use a task group to manage and await all tasks
        async with asyncio.TaskGroup() as tg:
            tg.create_task(distributor(client))
            tg.create_task(temperature_consumer())
            tg.create_task(humidity_consumer())


if __name__ == "__main__":
    asyncio.run(main())
```

And here's the same example **with** `aiomqtt-router`:

```python
import asyncio
import aiomqtt

from aiomqtt_router import AiomqttRouter

router = AiomqttRouter()


@router.subscribe("humidity/#")
def handle_humidity(message: aiomqtt.Message):
    print(f"[humidity/#] {message.payload}")


@router.subscribe("temperature/#")
async def handle_temperature(message: aiomqtt.Message):
    print(f"[temperature/#] {message.payload}")


async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
        await router(client)


if __name__ == "__main__":
    asyncio.run(main())
```
