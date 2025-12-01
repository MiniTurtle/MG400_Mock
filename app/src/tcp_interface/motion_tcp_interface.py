"""Motion Tcp Interface."""
# Copyright 2022 HarvestX Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from threading import Thread
from queue import Queue

from dobot_command.dobot_hardware import DobotHardware
from dobot_command.motion_command import MotionCommands
from utilities.function_parser import FunctionParser
from utilities.utils_for_command import generate_return_msg

from .tcp_interface_base import TcpInterfaceBase


class MotionTcpInterface(TcpInterfaceBase):
    """MotionTcpInterface"""
    logger: logging.Logger
    __socket_pool: Queue

    def __init__(self, ip: str, port: int, dobot: DobotHardware) -> None:
        super().__init__(ip, port, self.callback)

        self.logger = logging.getLogger("Motion Tcp Interface")
        self.__socket_pool = Queue()
        self.__dobot = dobot
        self.__motion_commands = MotionCommands(dobot)

        self.__motion_commands_parser = MotionCommands(DobotHardware())

    def callback(self, socket, max_receive_bytes):
        while True:
            connection, _ = socket.accept()
            # keep a reference if needed elsewhere
            self.__socket_pool.put(connection)
            Thread(
                target=self.__handle_client,
                args=(connection, max_receive_bytes),
                daemon=True,
            ).start()

    def __handle_client(self, connection, max_receive_bytes: int) -> None:
        with connection:
            while True:
                data = connection.recv(max_receive_bytes)
                if not data:
                    break
                recv = data.decode()
                self.logger.info(recv)
                # Execute motion command and always return a TCP response
                try:
                    # Use existing FunctionParser to dispatch to MotionCommands
                    result = FunctionParser.exec(self.__motion_commands_parser, recv)
                    # Success or handled failure: reply with current error id
                    error_id = self.__dobot.get_error_id()
                    res = generate_return_msg(int(error_id))
                    self.__dobot.motion_stack(recv)
                except ValueError as err:
                    # Unknown command or parse error: mirror dashboard behavior
                    self.logger.error(err)
                    res = "-"

                return_str = res + recv + ";"
                self.logger.info("RETURN: %s", return_str)
                connection.send(return_str.encode())
