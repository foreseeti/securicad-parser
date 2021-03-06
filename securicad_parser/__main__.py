# Copyright 2021-2022 Foreseeti AB <https://foreseeti.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pyright: reportUnknownMemberType=false
from __future__ import annotations

import base64
import contextlib
import importlib
import json
import logging
import os
import sys
import traceback
import typing
from configparser import ConfigParser
from dataclasses import dataclass
from io import StringIO
from logging import StreamHandler
from typing import Any, Callable, NamedTuple, Optional, Protocol

from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.connection import ConnectionParameters
from pika.credentials import PlainCredentials
from pika.spec import Basic, BasicProperties

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(StreamHandler(sys.stdout))


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
    parser: Parser,
    sub_parsers: dict[str, SubParser],
    parser_name: str,
    display_name: str,
    extension: Optional[str],
) -> Callable[[BlockingChannel, Basic.Deliver, BasicProperties, bytes], None]:
    def _callback(
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ):
        type_: Optional[str] = properties.type
        queue: str = properties.reply_to
        if type_ == "info":
            channel.basic_publish(
                "",
                queue,
                json.dumps(
                    {
                        "name": parser_name,
                        "display_name": display_name,
                        "extension": extension,
                        "sub_parsers": list(sub_parsers.keys()),
                    }
                ),
            )
            return

        stream = StringIO()
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
                result = parser.parse(
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
            result = json.dumps(result)
        except:
            stream.write(traceback.format_exc())
            channel.basic_publish(
                "",
                queue,
                stream.getvalue(),
                BasicProperties(message_id=properties.message_id, type="error"),  # type: ignore
            )
            return
        finally:
            log.info(stream.getvalue())

        channel.basic_publish(
            "",
            queue,
            result,
            BasicProperties(message_id=properties.message_id, type="success"),  # type: ignore
        )

    return _callback


def main():
    config = ConfigParser()
    config.read("setup.cfg")
    name = config["metadata"]["name"]
    if "enterprise_suite" in config:
        display_name = config["enterprise_suite"].get("display_name", name)
        extension = config["enterprise_suite"].get("extension")
    else:
        display_name = name
        extension = None

    parser = typing.cast(
        Parser, importlib.import_module(config["options"]["packages"].strip())
    )
    sub_parsers = {
        name: typing.cast(SubParser, importlib.import_module(module))
        for name, module in config["enterprise_suite.sub_parsers"].items()
    }

    connection = BlockingConnection(
        ConnectionParameters(
            host=os.environ["RABBIT_HOST"],
            credentials=PlainCredentials(
                os.environ["RABBIT_USERNAME"], os.environ["RABBIT_PASSWORD"]
            ),
        )
    )

    queue = f"parser-{name}"
    channel: BlockingChannel = connection.channel()
    channel.queue_declare(queue)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue,
        callback(parser, sub_parsers, name, display_name, extension),
        auto_ack=True,
    )
    channel.start_consuming()


if __name__ == "__main__":
    main()
