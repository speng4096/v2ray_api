import grpc
from grpc._channel import _Rendezvous
from v2ray.com.core.proxy.vmess import account_pb2
from v2ray.com.core.common.protocol import user_pb2
from v2ray.com.core.common.serial import typed_message_pb2
from v2ray.com.core.app.proxyman.command import command_pb2
from v2ray.com.core.app.proxyman.command import command_pb2_grpc
from v2ray.com.core.app.stats.command import command_pb2 as stats_command_pb2
from v2ray.com.core.app.stats.command import command_pb2_grpc as stats_command_pb2_grpc


class V2RayError(Exception):
    pass


class EmailExistsError(V2RayError):
    def __init__(self, email):
        self.email = email


class EmailNotFoundError(V2RayError):
    def __init__(self, email):
        self.email = email


class InboundNotFoundError(V2RayError):
    def __init__(self, inbound_tag):
        self.inbound_tag = inbound_tag


class Client(object):
    def __init__(self, address, port):
        self._channel = grpc.insecure_channel(f"{address}:{port}")

    @staticmethod
    def to_typed_message(message):
        return typed_message_pb2.TypedMessage(
            type=message.DESCRIPTOR.full_name,
            value=message.SerializeToString()
        )

    def user_traffic_downlink(self, email, reset=False):
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

    def user_traffic_uplink(self, email, reset=False):
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
        在一个传入代理中添加一个用户（仅支持 VMess）
        若email已存在，抛出EmailExistsError异常
        若inbound_tag不存在，抛出InboundNotFoundError异常
        """
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.AlterInbound(command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=self.to_typed_message(command_pb2.AddUserOperation(
                    user=user_pb2.User(
                        email=email,
                        level=level,
                        account=self.to_typed_message(account_pb2.Account(
                            id=user_id,
                            alter_id=alter_id
                        ))
                    )
                ))
            ))
            return user_id
        except _Rendezvous as e:
            if e.details().endswith(f"User {email} already exists."):
                raise EmailExistsError(email)
            elif e.details().endswith(f"handler not found: {inbound_tag}"):
                raise InboundNotFoundError(inbound_tag)
            else:
                raise e

    def remove_user(self, inbound_tag, email):
        """
        在一个传入代理中删除一个用户（仅支持 VMess）
        需几分钟生效，因为仅仅是把用户从用户列表中移除，没有移除对应的auth session，
        需要等这些session超时后，这个用户才会无法认证
        若email不存在，抛出EmailNotFoundError异常
        若inbound_tag不存在，抛出InboundNotFoundError异常
        """
        stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        try:
            stub.AlterInbound(command_pb2.AlterInboundRequest(
                tag=inbound_tag,
                operation=self.to_typed_message(command_pb2.RemoveUserOperation(
                    email=email
                ))
            ))
        except _Rendezvous as e:
            if e.details().endswith(f"User {email} not found."):
                raise EmailNotFoundError(email)
            elif e.details().endswith(f"handler not found: {inbound_tag}"):
                raise InboundNotFoundError(inbound_tag)
            else:
                raise e
