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

from dobot_command import robot_mode

class MotionTcpInterface(TcpInterfaceBase):
    """MotionTcpInterface"""
    logger: logging.Logger
    __socket_pool: Queue

    def __init__(self, ip: str, port: int, dobot: DobotHardware) -> None:
        super().__init__(ip, port, self.callback)

        self.__dobot_parser = DobotHardware()
        self.__motion_commands_parser = MotionCommands(self.__dobot_parser)
        self.logger = logging.getLogger("Motion Tcp Interface")
        self.__socket_pool = Queue()
        self.__dobot = dobot

        

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

                error_id = 0
                # Execute motion command and always return a TCP response
                try:
                    self.__dobot_parser.clear_error()
                    self.__dobot_parser.clear_motion_queue()
                    self.__dobot_parser.clear_wait()
                    self.__dobot_parser.set_robot_mode(robot_mode.MODE_ENABLE)
                    
                    # Use existing FunctionParser to dispatch to MotionCommands
                    result = FunctionParser.exec(self.__motion_commands_parser, recv)
                    if not result:
                        # Success or handled failure: reply with current error id
                        error_id = self.__dobot_parser.get_error_id()
                        if error_id == 0:
                            error_id = -1

                    res = generate_return_msg(int(error_id))
                    
                except ValueError as err:
                    # Unknown command or parse error: mirror dashboard behavior
                    self.logger.error(err)
                    res = "-"
                    error_id = -1

                if error_id == 0:
                    self.__dobot.motion_stack(recv)

                return_str = res + recv + ";"
                self.logger.info("RETURN: %s", return_str)
                connection.send(return_str.encode())
