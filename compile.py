"""从v2ray-core源码目录中寻找`.proto`文件并编译"""
import os
import sys
import shutil
import tempfile
import argparse
import distutils.dir_util


def walk(src, dst):
    # 导入路径类似'v2ray.com/core/common/serial/typed_message.proto'
    # 需整理好目录树
    tmp_dir = tempfile.mkdtemp()
    v2ray_dir = os.path.join(tmp_dir, 'v2ray.com')
    os.mkdir(v2ray_dir)
    shutil.copytree(src, os.path.join(v2ray_dir, 'core'))

    # 扫描proto文件
    proto_files = ''
    for root, dirs, files in os.walk(v2ray_dir):
        for file in files:
            if file.endswith(".proto"):
                proto_files += ' ' + os.path.join(root, file)
    if not proto_files:
        raise FileNotFoundError("未找到任何proto文件")

    # 编译
    command = f'{sys.executable} -m grpc.tools.protoc ' \
              f'-I={tmp_dir} ' \
              f'--python_out={dst} ' \
              f'--grpc_python_out={dst} ' + proto_files
    result = os.system(command)
    # 编译后*_pb2_grpc.py和*_pb2.py分别在v2ray.com和v2ray目录中
    # 将他们合并到一个目录
    distutils.dir_util.copy_tree(os.path.join(dst, 'v2ray.com/core/'), os.path.join(dst, 'v2ray/com/core/'))
    shutil.rmtree(tmp_dir)
    shutil.rmtree(os.path.join(dst, 'v2ray.com'))
    return result


def main():
    # 解析参数
    node = argparse.ArgumentParser()
    node.add_argument('-s', '--src', required=True, help="v2ray-core源码目录")
    node.add_argument('-d', '--dst', default='./', help="编译后的输出目录")
    options = node.parse_args()
    # 确认参数
    names = {'app', 'common', 'main', 'proxy', 'transport'}
    if not names.issubset(set(os.listdir(options.src))):
        raise Exception(f"'{options.src}'不是v2ray-core源码目录")
    if not os.path.exists(options.dst):
        raise FileNotFoundError(f"输出'{options.src}'不存在")

    return walk(options.src, options.dst)


if __name__ == '__main__':
    main()
