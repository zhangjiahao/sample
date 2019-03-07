# -*- coding: utf-8 -*-

"""
In windows: scp necessary files to a linux server under virtual box
        and execute the compile operation, after that, copy the strategy
        to current directory
In linux: execute strategy so compile operation, if success, make the result
        so exist in current directory
"""

import atexit
import os
import shutil
import socket
import platform
import sys
import uuid

import my.sdp
import paramiko
from my.sdp.tools.pyxgen import PyxGenerator

"""
The vm build server configuration
"""
host_ip = '192.168.56.101'
username = 'mycap'
password = '123456'


class VMExecutor:
    def __init__(self):
        super(VMExecutor, self).__init__()
        self._create_scp(host_ip, 22, username, password)
        atexit.register(self.close)

    def _create_scp(self, server, port, user, passwd):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(server, port, user, passwd, timeout=2, auth_timeout=1.5)
        except socket.timeout:
            print("Can't connect to server, please start the virtual box first !!!")
            sys.exit(0)
        except Exception as e:
            print("Some error happened, please contact us!!!\n", e)
            sys.exit(-1)
        self.client = client
        self.sftp = client.open_sftp()

    def put(self, source, dest):
        self.sftp.put(source, dest)

    @staticmethod
    def _normalize_directory(directory):
        directory = directory.replace("\\", "/")
        while directory.endswith("/"):
            directory = directory[:-1]
        return directory

    def _check_remote_dir(self, directory):
        try:
            self.sftp.lstat(directory)
            return True
        except Exception:
            return False

    def _ensure_remote_dir(self, directory):
        if not self._check_remote_dir(directory):
            try:
                self.sftp.mkdir(directory)
            except Exception:
                directory = self._normalize_directory(directory)
                self._ensure_remote_dir(directory.rsplit("/", 1)[0])
                self._ensure_remote_dir(directory)

    def bulk_put(self, conf):
        for source, dest in conf:
            if os.path.isdir(source):
                source = os.path.abspath(source)
                for root, dirs, files in os.walk(source):
                    for file in files:
                        src_file = os.path.join(root, file)
                        dest_file = src_file.replace(source, dest)
                        dest_file = dest_file.replace('\\', '/')
                        self._ensure_remote_dir(os.path.dirname(dest_file))
                        self.put(src_file, dest_file)
            else:
                self._ensure_remote_dir(os.path.dirname(dest))
                dest = dest.replace('\\', '/')
                self.put(source, dest)

    def get(self, source, dest):
        # print("get", source, dest)
        self.sftp.get(source, dest)

    def make(self, directory):
        cmd = 'cd %s;make' % directory
        _, stdout_, stderr = self.client.exec_command(cmd)
        print('='*30 + 'Compile Output' + '='*30)
        print(''.join(stdout_.readlines()))
        print(''.join(stderr.readlines()))
        return stdout_.channel.recv_exit_status()

    def setup_make(self, directory):
        cmd = 'cd %s;python3.5 setup.py build_ext --inplace' % directory
        _, stdout_, stderr = self.client.exec_command(cmd)
        print('='*30 + 'Compile Output' + '='*30)
        print(''.join(stdout_.readlines()))
        print(''.join(stderr.readlines()))
        return stdout_.channel.recv_exit_status()

    def rm(self, directory):
        try:
            if not directory.startswith('/tmp'):
                print("rm dir can't be", directory)
                return
            self.client.exec_command('rm -r %s' % directory)
        except Exception:
            print("rm remote", directory, "failed")

    def rename(self, directory):
        try:
            if not directory.startswith('/tmp'):
                print("rename dir cant't be", directory)
                return
            self.client.exec_command('mv %s %s' % (directory, directory+'_error'))
        except Exception:
            pass

    def close(self):
        self.sftp.close()


class HostExecutor:
    def _ensure_directory(self, directory):
        if not os.path.isdir(directory):
            os.makedirs(directory)

    def bulk_put(self, conf):
        for source, dest in conf:
            self._ensure_directory(os.path.dirname(dest))
            if os.path.isfile(source):
                shutil.copy(source, dest)
            else:
                shutil.copytree(source, dest)

    def make(self, directory):
        cmd = "cd %s; make" % directory
        return os.system(cmd)

    def setup_make(self, directory):
        cmd = 'cd %s;python3.5 setup.py build_ext --inplace' % directory
        return os.system(cmd)

    def get(self, source, dest):
        if source.startswith('/tmp'):
            shutil.copy(source, dest)
        else:
            print("fetch so failed!!! for path", source)

    def rm(self, source):
        if source.startswith('/tmp'):
            shutil.rmtree(source)


def generate_compile_dir(option='so'):
    if option == 'so':
        temp_dir = 'pysdp_compile_st_' + str(uuid.uuid4())
    elif option == 'tradelist':
        temp_dir = 'pysdp_compile_tradelist_' + str(uuid.uuid4())
    return os.path.join('/tmp', temp_dir)


def compile(st_path=".", st_files=["st.py"], auto_search_path=False):
    """
    :param st_path: absolute or relative(to current directory) path of strategy directory
    :param st_files: list of files to be compiled
    :return: return nothing but print execute progress and generate so if success
    """
    compile_dir = generate_compile_dir()
    sdp_path = os.path.dirname(my.sdp.__file__)
    if not auto_search_path:
        to_put_list = [
            (os.path.join(sdp_path, 'core'), os.path.join(compile_dir, 'core')),
            (os.path.join(sdp_path, 'api.py'), os.path.join(compile_dir, 'api.py')),
            (os.path.join(sdp_path, 'src', 'Makefile'), os.path.join(compile_dir, 'Makefile')),
            (os.path.join(st_path, 'st.pyx'), os.path.join(compile_dir, 'st.pyx')),
        ]
        for f in st_files:
            st_file = os.path.join(st_path, f)
            if not os.path.isfile(st_file):
                print("strategy file", st_file, "not exist!!!!")
                sys.exit(0)
            else:
                to_put_list.append((st_file, os.path.join(compile_dir, f)))
    else:
        py_file = os.path.join(st_path, st_files[0])
        pyx_path = os.path.join(st_path, 'compile_temp')
        PyxGenerator(py_file).generate_pyx(path=os.path.join(pyx_path, "st.pyx"))
        to_put_list = [
            (os.path.join(sdp_path, 'core'), os.path.join(compile_dir, 'core')),
            (os.path.join(sdp_path, 'api.py'), os.path.join(compile_dir, 'api.py')),
            (os.path.join(sdp_path, 'src', 'Makefile'), os.path.join(compile_dir, 'Makefile')),
            (os.path.join(pyx_path, 'st.pyx'), os.path.join(compile_dir, 'st.pyx')),
        ]

    source_dir = compile_dir.replace('\\', '/')
    if platform.system() == "Windows":
        f_carrier = VMExecutor()
    else:
        f_carrier = HostExecutor()
    f_carrier.bulk_put(to_put_list)
    status = f_carrier.make(source_dir)
    if status == 0:
        st_name = st_files[0][:-2] + 'so'
        f_carrier.get(source_dir + '/st.so', os.path.join('.', st_name))
        print("Compile success and load file in current directory")
        f_carrier.rm(source_dir)
    else:
        print("Compile failed!!! please check the st.py")


def compile_tradelist(st_path='.', st_files=["tradelist_gen.py"]):
    compile_dir = generate_compile_dir(option='tradelist')

    to_put_list = [
        (os.path.join(st_path, 'setup.py'), os.path.join(compile_dir, 'setup.py')),
    ]
    for f in st_files:
        st_file = os.path.join(st_path, f)
        if not os.path.isfile(st_file):
            print("file", st_file, "not exist!!!!")
            sys.exit(0)
        else:
            to_put_list.append((st_file, os.path.join(compile_dir, f)))

    source_dir = compile_dir.replace('\\', '/')
    if platform.system() == "Windows":
        f_carrier = VMExecutor()
    else:
        f_carrier = HostExecutor()
    f_carrier.bulk_put(to_put_list)
    status = f_carrier.setup_make(source_dir)
    if status == 0:
        st_name = st_files[0].split('.')[0] + '.cpython-35m-x86_64-linux-gnu.so'
        f_carrier.get(source_dir + '/' + st_name, os.path.join('.', st_name))
        print("Compile success and load file in current directory")
        f_carrier.rm(source_dir)
    else:
        print("Compile failed!!! please check the tradelist_gen.py")


if __name__ == "__main__":
    compile()
