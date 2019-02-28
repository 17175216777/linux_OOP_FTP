import os
import json
import shutil
import hashlib
import struct
import socketserver


class Server(socketserver.BaseRequestHandler):
    current_path = None

    def handle(self):
        """
        映射接收客户端命令,并跳转指定方法
        :return:
        """
        name = self.recv()
        if hasattr(self, name):
            getattr(self, name)()

    def send(self, msg):
        """
        防粘包,发送消息方法
        :param msg:
        :return:
        """
        msg = msg.encode()
        num = struct.pack("i", len(msg))
        self.request.send(num)
        self.request.send(msg)

    def recv(self):
        """
        防粘包,收取消息方法
        :return: 收取到的消息
        """
        num_bytes = self.request.recv(4)
        num = struct.unpack("i", num_bytes)[0]
        msg = self.request.recv(num).decode()
        return msg

    def login(self):
        """
        帐号登陆
        :return:
        """
        user_pwd = self.recv()
        ret = self.read_account(user_pwd)
        self.send(ret)
        if ret == "1":
            self.current_path = os.path.join("D:\\", user_pwd.split("|")[0])
            self.send(self.current_path)
            if not os.path.exists(self.current_path):
                os.mkdir(self.current_path)
            self.handle()
        if ret == "0":
            self.handle()

    def register(self):
        """
        账号注册
        :return:
        """
        user_pwd = self.recv()
        ret = self.auth_account(user_pwd)
        self.send(ret)
        if ret == "1":
            self.handle()
        if ret == "0":
            self.handle()

    def exit(self):
        self.handle()

    @staticmethod
    def md5(file_path):
        """
        计算文件的md5
        :param file_path:
        :return:
        """
        read_num = 0
        file_size = os.path.getsize(file_path)
        file_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while read_num < file_size:
                read_size = f.read(1024)
                file_md5.update(read_size)
                read_num += len(read_size)
        return file_md5.hexdigest()

    def last_dir(self):
        """
        返回上一层
        :return:
        """
        ret = self.recv()
        if ret == "error":
            self.handle()
        else:
            self.current_path = ret
            self.handle()

    def next_dir(self):
        """
        进入下一层
        :return:
        """
        self.show_dir(status=False)
        ret = self.recv()
        if ret == "right":
            dir_name = self.recv()
            if dir_name != "error":
                new_path = os.path.join(self.current_path, dir_name)
                if os.path.isdir(new_path):
                    self.send("right")
                    self.current_path = new_path
                    self.handle()
                else:
                    self.send("error")
                    self.next_dir()
            else:
                self.next_dir()
        else:
            self.handle()

    def show_dir(self, status=True):
        """
        显示当前路径下所有文件和文件夹
        :return:
        """
        lst = os.listdir(self.current_path)
        self.send(json.dumps(lst))
        if status is True:
            self.handle()

    def mk_dir(self):
        """
        创建文件夹
        """
        self.show_dir(False)
        dir_name = self.recv()
        new_dir = os.path.join(self.current_path, dir_name)
        if os.path.exists(new_dir):
            self.send("error")
            self.mk_dir()
        else:
            self.send("right")
            os.mkdir(new_dir)
            self.handle()

    def rm_dir(self):
        """
        删除文件夹
        :return:
        """
        self.show_dir(False)
        ret = self.recv()
        if ret == "right":
            dir_name = self.recv()
            # print(dir_name)
            if dir_name != "error":
                # print(os.path.join(self.current_path, dir_name))
                shutil.rmtree(os.path.join(self.current_path, dir_name))
                self.handle()
            else:
                self.rm_dir()
        else:
            self.handle()

    def mk_file(self):
        """
        用户创建文件
        :return:
        """
        self.show_dir(False)
        file_name = self.recv()
        new_file = os.path.join(self.current_path, file_name)
        if os.path.exists(new_file):
            self.send("error")
            self.mk_file()
        else:
            self.send("right")
            open(new_file, "w")
            self.handle()

    def rm_file(self):
        self.show_dir(False)
        ret = self.recv()
        if ret == "right":
            file_name = self.recv()
            if file_name != "error":
                os.remove(os.path.join(self.current_path, file_name))
                self.handle()
            else:
                self.rm_file()
        else:
            self.handle()

    def download(self):
        """
        用户下载文件
        :return:
        """
        self.show_dir(status=False)
        ret = self.recv()
        if ret == "right":
            file_name = self.recv()
            if file_name != "error":
                self.send("right")
                file_path = os.path.join(self.current_path, file_name)
                if os.path.isfile(file_path):
                    file_name = os.path.basename(file_path)
                    file_md5 = self.md5(file_path)
                    file_size = os.path.getsize(file_path)
                    dic = {
                        "file_name": file_name,
                        "file_md5": file_md5,
                        "file_size": file_size,
                    }
                    json_bytes = json.dumps(dic)
                    num = struct.pack("i", len(json_bytes))
                    self.request.send(num)
                    self.request.send(json_bytes.encode())
                    # send_size = 0
                    with open(file_path, "rb") as f:
                        num = self.recv()
                        if num == "right":
                            send_size = file_size
                        else:
                            send_size = f.seek(int(num))   # 断点续传移动光标
                        while send_size < file_size:
                            read_data = f.read(1024)
                            send_data = self.request.send(read_data)
                            send_size += send_data
                    ret = self.request.recv(1024).decode()
                    print(ret)
                    if ret == "right":
                        self.handle()
                    if ret == "error":
                        self.download()
                else:
                    self.send("error")
                    self.download()
            else:
                self.download()
        else:
            self.handle()

    def uploading(self):
        """
        用户上传文件
        :return:
        """
        num_bytes = self.request.recv(4)
        num = struct.unpack("i", num_bytes)[0]
        json_bytes = self.request.recv(num).decode()
        dic = json.loads(json_bytes)
        file_name = dic["file_name"]
        file_md5 = dic["file_md5"]
        file_size = dic["file_size"]
        file_path = os.path.join(self.current_path, file_name)
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        with open(file_path, "ab") as f:
            recv_size = f.seek(0, 2)
            # 将光标移动到文件末尾,并返回已传输的文件字节数
            if recv_size == file_size:
                self.send("right")
            else:
                self.send(str(recv_size))
            # 上传功能的断点续传,将已收到的文件字节数发送给客户端
            while recv_size < file_size:
                recv_data = self.request.recv(1024)
                recv_size += len(recv_data)
                f.write(recv_data)
        new_md5 = self.md5(file_path)
        if new_md5 == file_md5:
            self.send("right")
            self.handle()
        else:
            self.send("error")
            self.uploading()

    @staticmethod
    def read_account(user_pwd):
        """
        读取用户信息
        :param user_pwd: 帐号密码
        :return:
        """
        file_dir = os.path.dirname(__file__)
        with open(rf"{file_dir}\account.db", "r") as f:
            for i in f:
                if user_pwd == i.strip():
                    return "1"
            else:
                return "0"

    @staticmethod
    def auth_account(user_pwd):
        """
        验证帐号密码
        :param user_pwd: 帐号密码
        :return: "0","1"验证失败或成功
        """
        file_dir = os.path.dirname(__file__)
        with open(rf"{file_dir}\account.db", "r") as f:
            for i in f:
                if user_pwd.split("|")[0] == i.strip().split("|")[0]:
                    return "0"
            else:
                with open(rf"{file_dir}\account.db", "a") as f1:
                    f1.write(user_pwd+"\n")
                    return "1"


if __name__ == "__main__":
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 10010), Server)
    server.serve_forever()
