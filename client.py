import os
import sys
sys.path.append(os.path.dirname(__file__))
import grpc
from grpc._channel import _Rendezvous
from errors import *
from v2ray.com.core.common.net import port_pb2, address_pb2
from v2ray.com.core import config_pb2 as core_config_pb2
from v2ray.com.core.proxy.vmess import account_pb2
from v2ray.com.core.proxy.vmess.inbound import config_pb2 as vmess_inbound_config_pb2
from v2ray.com.core.common.protocol import user_pb2
from v2ray.com.core.common.serial import typed_message_pb2
from v2ray.com.core.app.proxyman import config_pb2 as proxyman_config_pb2
from v2ray.com.core.app.proxyman.command import command_pb2
from v2ray.com.core.app.proxyman.command import command_pb2_grpc
from v2ray.com.core.app.stats.command import command_pb2 as stats_command_pb2
from v2ray.com.core.app.stats.command import command_pb2_grpc as stats_command_pb2_grpc


def to_typed_message(message):
    return typed_message_pb2.TypedMessage(
        type=message.DESCRIPTOR.full_name,
        value=message.SerializeToString()
    )


def ip2bytes(ip: str):
    return bytes([int(i) for i in ip.split('.')])


class Proxy(object):
    """代理配置的基类"""

    def __init__(self):
        self.message = None


class VMessInbound(Proxy):
    """VMess传入连接配置"""

    def __init__(self, *users: dict):
        """
        :param users: 包含'email','level','user_id','alter_id'字段的字典
        """
        super(VMessInbound, self).__init__()
        self.message = to_typed_message(
            vmess_inbound_config_pb2.Config(
                user=[
                    user_pb2.User(
                        email=u['email'],
                        level=u['level'],
                        account=to_typed_message(account_pb2.Account(
                            id=u['user_id'],
                            alter_id=u['alter_id']
                        ))
                    ) for u in users
                ]
            )
        )


class Client(object):
    def __init__(self, address, port):
        self._channel = grpc.insecure_channel(f"{address}:{port}")

    def get_user_traffic_downlink(self, email, reset=False):
        """
        获取用户下行流量，单位：字节
        若该email未产生流量或email有误，返回None
        :param email: 邮箱
        :param reset: 是否重置计数器
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self._channel)
        try:
            return stub.GetStats(stats_command_pb2.GetStatsRequest(
                name=f"user>>>{email}>>>traffic>>>downlink",
                reset=reset
            )).stat.value
        except grpc.RpcError:
            return None

    def get_user_traffic_uplink(self, email, reset=False):
        """
        获取用户上行流量，单位：字节
        若该email未产生流量或email有误，返回None
        :param email: 邮箱
        :param reset: 是否重置计数器
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self._channel)
        try:
            return stub.GetStats(stats_command_pb2.GetStatsRequest(
                name=f"user>>>{email}>>>traffic>>>uplink",
                reset=reset
            )).stat.value
        except grpc.RpcError:
            return None

    def add_user(self, inbound_tag, user_id, email, level, alter_id):
        """
        在一个传入连接中添加一个用户（仅支持 VMess）
        若email已存在，抛出EmailExistsError异常
        若inbound_tag不存在，抛出InboundNotFoundError异常
        """
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.AlterInbound(command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=to_typed_message(command_pb2.AddUserOperation(
                    user=user_pb2.User(
                        email=email,
                        level=level,
                        account=to_typed_message(account_pb2.Account(
                            id=user_id,
                            alter_id=alter_id
                        ))
                    )
                ))
            ))
            return user_id
        except _Rendezvous as e:
            details = e.details()
            if details.endswith(f"User {email} already exists."):
                raise EmailExistsError(details, email)
            elif details.endswith(f"handler not found: {inbound_tag}"):
                raise InboundNotFoundError(details, inbound_tag)
            else:
                raise V2RayError(details)

    def remove_user(self, inbound_tag, email):
        """
        在一个传入连接中删除一个用户（仅支持 VMess）
        需几分钟生效，因为仅仅是把用户从用户列表中移除，没有移除对应的auth session，
        需要等这些session超时后，这个用户才会无法认证
        若email不存在，抛出EmailNotFoundError异常
        若inbound_tag不存在，抛出InboundNotFoundError异常
        """
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.AlterInbound(command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=to_typed_message(command_pb2.RemoveUserOperation(
                    email=email
                ))
            ))
        except _Rendezvous as e:
            details = e.details()
            if details.endswith(f"User {email} not found."):
                raise EmailNotFoundError(details, email)
            elif details.endswith(f"handler not found: {inbound_tag}"):
                raise InboundNotFoundError(details, inbound_tag)
            else:
                raise V2RayError(details)

    def add_inbound(self, tag, address, port, proxy: Proxy):
        """
        增加传入连接
        :param tag: 此传入连接的标识
        :param address: 监听地址
        :param port: 监听端口
        :param proxy: 代理配置
        """
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.AddInbound(command_pb2.AddInboundRequest(
                inbound=core_config_pb2.InboundHandlerConfig(
                    tag=tag,
                    receiver_settings=to_typed_message(
                        proxyman_config_pb2.ReceiverConfig(
                            port_range=port_pb2.PortRange(
                                From=port,
                                To=port,
                            ),
                            listen=address_pb2.IPOrDomain(
                                ip=ip2bytes(address),  # 4字节或16字节
                            ),
                            allocation_strategy=None,
                            stream_settings=None,
                            receive_original_destination=None,
                            domain_override=None,
                            sniffing_settings=None
                        )
                    ),
                    proxy_settings=proxy.message
                )
            ))
        except _Rendezvous as e:
            details = e.details()
            if details.endswith("address already in use"):
                raise AddressAlreadyInUseError(details, port)
            else:
                raise V2RayError(details)

    def remove_inbound(self, tag):
        """删除传入连接"""
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.RemoveInbound(command_pb2.RemoveInboundRequest(
                tag=tag
            ))
        except _Rendezvous as e:
            details = e.details()
            if details == 'not enough information for making a decision':
                raise InboundNotFoundError(details, tag)
            else:
                raise V2RayError(details)
