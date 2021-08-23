# pyright: reportUnknownMemberType=false
from __future__ import annotations

import base64
import contextlib
import importlib
import json
import logging
import os
import typing
from configparser import ConfigParser
from dataclasses import dataclass
from io import StringIO
from logging import StreamHandler
from typing import Any, Callable, NamedTuple, Protocol

from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.connection import ConnectionParameters
from pika.credentials import PlainCredentials
from pika.spec import Basic, BasicProperties


log = logging.getLogger()
log.setLevel(logging.INFO)
handler = StreamHandler(StringIO())
log.addHandler(handler)


@dataclass
class SubParserInput:
    sub_parser: str
    data: bytes


class SubParserOutput(NamedTuple):
    sub_parser: str
    data: Any


@dataclass
class Message:
    metadata: dict[str, Any]
    data: list[SubParserInput]


class Parser(Protocol):
    def parse(
        self, data: list[SubParserOutput], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        ...


class SubParser(Protocol):
    def parse(self, data: bytes, metadata: dict[str, Any]) -> Any:
        ...


def callback(
    parser: Parser, sub_parsers: dict[str, SubParser], queue_name: str
) -> Callable[[BlockingChannel, Basic.Deliver, BasicProperties, bytes], None]:
    def _callback(
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ):
        stream = StringIO()
        handler.setStream(stream)
        try:
            data = json.loads(body)
            message = Message(
                data["metadata"],
                [
                    SubParserInput(entry["sub_parser"], base64.b64decode(entry["data"]))
                    for entry in data["data"]
                ],
            )
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                channel.basic_publish(
                    "",
                    queue_name,
                    json.dumps(
                        parser.parse(
                            [
                                SubParserOutput(
                                    entry.sub_parser,
                                    sub_parsers[entry.sub_parser].parse(
                                        entry.data, message.metadata
                                    ),
                                )
                                for entry in message.data
                            ],
                            message.metadata,
                        )
                    ),
                    BasicProperties(message_id=properties.message_id, type="success"),  # type: ignore
                )
        except:
            log.exception("parser exception")
            channel.basic_publish(
                "",
                queue_name,
                stream.getvalue(),
                BasicProperties(message_id=properties.message_id, type="error"),  # type: ignore
            )

    return _callback


def main():
    config = ConfigParser()
    config.read("setup.cfg")
    name = config["metadata"]["name"]
    display_name = config["enterprise_suite"].get("display_name", name)
    extension = config["enterprise_suite"].get("extension")

    parser = typing.cast(
        Parser, importlib.import_module(config["options"]["packages"].strip())
    )
    sub_parsers = {
        name: typing.cast(SubParser, importlib.import_module(module))
        for name, module in config["enterprise_suite.sub_parsers"].items()
    }

    connection = BlockingConnection(
        ConnectionParameters(
            host="host.docker.internal",
            credentials=PlainCredentials(
                os.environ["RABBIT_USERNAME"], os.environ["RABBIT_PASSWORD"]
            ),
        )
    )

    parser_queue_name = "parser"
    waiting_queue_name = f"{name}-waiting"
    done_queue_name = f"{name}-done"

    channel: BlockingChannel = connection.channel()
    channel.queue_declare(parser_queue_name)
    channel.queue_declare(waiting_queue_name)
    channel.queue_declare(done_queue_name)
    channel.basic_publish(
        "",
        parser_queue_name,
        json.dumps(
            {
                "name": name,
                "display_name": display_name,
                "extension": extension,
                "sub_parsers": list(sub_parsers.keys()),
            }
        ),
    )

    channel.basic_consume(
        waiting_queue_name,
        callback(parser, sub_parsers, done_queue_name),
        auto_ack=True,
    )
    channel.start_consuming()


if __name__ == "__main__":
    main()
