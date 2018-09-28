## V2Ray-API

### 安装

1. 下载

   ```bash
   git clone https://github.com/spencer404/v2ray-api.git
   ```

2. 安装依赖

   ```bash
   pip3.6 install grpcio grpcio-tools
   ```

3. 编译proto到v2ray目录（此步可忽略，默认为v3.41）

   ```bash
   cd v2ray-api
   # 下载v2ray-core源码
   git clone https://github.com/v2ray/v2ray-core.git
   # 清空旧的v2ray目录
   rm -rf v2ray
   mkdir v2ray
   # 编译到v2ray目录
   python3.6 compile.py -s v2ray-core -d .
   ```



### 使用

```python
import uuid
from client import Client, VMessInbound

# 创建连接
c = Client("example.com", 8080)

# 上行流量（字节）
# 若未产生流量或email有误，返回None
c.get_user_traffic_uplink('me@example.com')

# 下行流量（字节）
# 若未产生流量或email有误，返回None
c.get_user_traffic_downlink('me@example.com')

# 在一个传入连接中添加一个用户（仅支持 VMess）
# 若用户不存在，抛出EmailExistsError异常
# 若inbound_tag不存在，抛出InboundNotFoundError异常
c.add_user('inbound_tag', uuid.uuid4().hex, 'me@example.com', 0, 32)

# 在一个传入连接中删除一个用户（仅支持 VMess）
# 若用户不存在，抛出EmailNotFoundError异常
# 若inbound_tag不存在，抛出InboundNotFoundError异常
c.remove_user('inbound_tag', 'me@example.com')

# 增加传入连接
# 若端口已被占用，抛出AddressAlreadyInUseError异常
vmess = VMessInbound(
        {
            'email': 'me@example.com',
            'level': 0,
            'alter_id': 16,
            'user_id': uuid.uuid4().hex
        }
    )
c.add_inbound("inbound_tag", '0.0.0.0', 9002, vmess)

# 移除传入连接
# 若inbound_tag不存在，抛出InboundNotFoundError异常
c.remove_inbound("inbound_tag")
```



### 参考

1. [Golang调用API示例](https://medium.com/@TachyonDevel/%E8%B0%83%E7%94%A8-v2ray-%E6%8F%90%E4%BE%9B%E7%9A%84-api-%E6%8E%A5%E5%8F%A3%E8%BF%9B%E8%A1%8C%E7%94%A8%E6%88%B7%E5%A2%9E%E5%88%A0%E6%93%8D%E4%BD%9C-adf9ff972973)
2. [Python gRPC示例](https://www.jianshu.com/p/14e6f5217f40)
3. [V2Ray-Core源码中的`*.proto`文件](https://github.com/v2ray/v2ray-core)
4. [V2Ray测试用例的例子](https://github.com/v2ray/v2ray-core/blob/29ad2cbbdb4445b1a8d554d102ef2ac9c58655dd/testing/scenarios/command_test.go)
