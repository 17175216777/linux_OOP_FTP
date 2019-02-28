import os
import json
import hashlib
import struct
import socket


class Client:
    def __init__(self, ip_port):
        self.ip_port = ip_port
        self.client = socket.socket()
        self.client.connect(ip_port)
        self.current_path = None
        self.default_path = None
        self.main()

    def main(self):
        """
        初次进入选择功能
        :return:
        """
        choice = input("""\n欢迎进入垃圾云盘!!\n\t1 登陆\n\t2 注册\n\t3 退出\n\t请选择:""").strip()
        if choice == "1":
            self.login()
        if choice == "2":
            self.register()
        if choice == "3":
            self.client.close()
        else:
            self.main()

    def handle(self):
        """
        登陆成功选择操作
        :return:
        """
        dic = {"返回上一层": "last_dir",
               "进入下一层": "next_dir",
               "查看所有文件": "show_dir",
               "创建文件夹": "mk_dir",
               "删除文件夹": "rm_dir",
               "创建文件": "mk_file",
               "删除文件": "rm_file",
               "上传文件": "uploading",
               "下载文件": "download",
               "退出到登陆": "exit"
               }
        print("="*30)
        lst = list(dic.keys())
        for k, v in enumerate(lst, 0):
            print(k, v)
        num = input("请选择操作:")
        if num.isdigit() and (-1 < int(num) < len(lst)):
            key = lst[int(num)]
            self.send(dic[key])
            if hasattr(self, dic[key]):
                getattr(self, dic[key])()
        else:
            print("请重新选择!!")
            return self.handle()

    def send(self, msg):
        """
        防粘包,发送消息方法
        :param msg:
        :return:
        """
        msg = msg.encode()
        num = struct.pack("i", len(msg))
        self.client.send(num)
        self.client.send(msg)

    def recv(self):
        """
        防粘包,收取消息方法
        :return: 收取到的消息
        """
        num_bytes = self.client.recv(4)
        num = struct.unpack("i", num_bytes)[0]
        msg = self.client.recv(num).decode()
        return msg

    def login(self):
        """
        用户登录
        :return:
        """
        self.send("login")
        print("欢迎来到登录界面!!")
        username = input("请输入帐号:").strip()
        password = input("请输入密码:").strip()
        if len(username) < 20 and len(password) < 20:
            pwd_md5 = hashlib.md5(password.encode()).hexdigest()
            user_pwd = username+"|"+pwd_md5
            self.send(user_pwd)
            ret = self.recv()
            if ret == "1":
                print("登陆成功!!")
                current_path = self.recv()
                self.current_path = current_path
                self.default_path = current_path
                self.handle()

            if ret == "0":
                print("登陆失败!!")
                self.main()

    def register(self):
        """
        用户账号注册
        :return:
        """
        self.send("register")
        print("欢迎来到注册界面!!")
        username = input("请输入帐号:").strip()
        password = input("请输入密码:").strip()
        if len(username) < 20 and len(password) < 20:
            pwd_md5 = hashlib.md5(password.encode()).hexdigest()
            user_pwd = username + "|" + pwd_md5
            self.send(user_pwd)
            ret = self.recv()
            if ret == "1":
                print("注册成功!!")
                self.login()
            if ret == "0":
                print("注册失败!!重新注册!!")
                self.register()

    def exit(self):
        self.send("exit")
        self.main()

    @staticmethod
    def md5(file_path):
        """
        计算文件的md5值
        :param file_path: 需要计算的文件路径
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
        if self.current_path == self.default_path:
            print("当前文件夹已是顶级文件夹!!")
            self.send("error")
        else:
            last_dir = os.path.dirname(self.current_path)
            self.current_path = last_dir
            self.send(last_dir)
        self.handle()

    def next_dir(self):
        """
        进入下一层
        :return:
        """
        lst = self.show_dir(False)
        if lst:
            self.send("right")
            dir_name = input("请选择你要进入的文件夹:")
            if dir_name.isdigit() and (-1 < int(dir_name)-1 < len(lst)):
                self.send(lst[int(dir_name) - 1])
                ret = self.recv()
                if ret == "error":
                    print("文件夹切换失败!!")
                    self.next_dir()
                else:
                    self.current_path = os.path.join(self.current_path, lst[int(dir_name) - 1])
                    print("文件夹切换成功!!")
                    self.handle()
            else:
                self.send("error")
                self.next_dir()
        else:
            self.send("error")
            print("该文件夹内无文件,请重新操作")
            self.handle()

    def show_dir(self, status=True):
        """
        显示当前目录下所有文件夹及文件
        :return:
        """
        print(f"当前文件目录为:{self.current_path}")
        str_lst = self.recv()
        lst = json.loads(str_lst)
        print("该目录下共有以下文件:")
        for k, v in enumerate(lst, 1):
            print(k, v)
        if status is True:
            self.handle()
        else:
            return lst

    def mk_dir(self):
        """
        创建文件夹
        :return:
        """
        self.show_dir(False)
        dir_name = input("请输入你要创建的文件夹名称:")
        self.send(dir_name)
        msg = self.recv()
        if msg == "error":
            self.mk_dir()
        else:
            print("文件夹创建成功!!")
            self.handle()

    def rm_dir(self):
        """
        删除文件夹
        :return:
        """
        lst = self.show_dir(False)
        if lst:
            self.send("right")
            dir_name = input("请选择你要删除的文件夹:")
            if dir_name.isdigit() and (-1 < int(dir_name)-1 < len(lst)-1):
                self.send(lst[int(dir_name)-1])
                print("文件夹删除成功!!")
                self.handle()
            else:
                print("文件夹删除失败!!")
                self.send("error")
                self.rm_dir()
        else:
            print("文件夹下无文件,请重新操作!!")
            self.send("error")
            self.handle()

    def mk_file(self):
        """
        创建文件
        :return:
        """
        self.show_dir(False)
        file_name = input("请输入你要创建的文件名称:")
        self.send(file_name)
        msg = self.recv()
        if msg == "error":
            print("文件创建失败!!")
            self.mk_file()
        else:
            print("文件夹创建成功!!")
            self.handle()

    def rm_file(self):
        """
        删除文件
        :return:
        """
        lst = self.show_dir(False)
        if lst:
            self.send("right")
            file_name = input("请选择你要删除的文件:")
            if file_name.isdigit() and (-1 < int(file_name)-1 < len(lst) - 1):
                self.send(lst[int(file_name) - 1])
                print("文件删除成功!!")
                self.handle()
            else:
                print("文件删除失败!!")
                self.send("error")
                self.rm_dir()
        else:
            self.send("error")
            print("该文件夹下无文件!!")
            self.handle()

    def download(self):
        """
        用户下载功能
        :return:
        """
        lst = self.show_dir(False)
        if lst:
            self.send("right")
            dir_name = input("请选择你要下载的文件:")
            if dir_name.isdigit() and (-1 < int(dir_name) - 1 < len(lst)):
                self.send(lst[int(dir_name) - 1])
                ret = self.recv()
                if ret == "error":
                    print("文件下载失败!!")
                    self.download()
                else:
                    num_bytes = self.client.recv(4)
                    num = struct.unpack("i", num_bytes)[0]
                    json_bytes = self.client.recv(num).decode()
                    dic = json.loads(json_bytes)
                    file_name = dic["file_name"]
                    file_md5 = dic["file_md5"]
                    file_size = dic["file_size"]
                    file_path = os.path.join("D:\\Downloads", file_name)
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
                        # 断点续传,将已收到的文件字节数发送给客户端
                        while recv_size < file_size:
                            recv_data = self.client.recv(1024)
                            recv_size += len(recv_data)
                            self.progress(recv_size/file_size)
                            f.write(recv_data)
                    new_md5 = self.md5(file_path)
                    if new_md5 == file_md5:
                        self.client.send("right".encode())
                        print("文件下载成功!!")
                        self.handle()
                    else:
                        self.client.send("error".encode())
                        self.download()
            else:
                self.send("error")
                self.download()
        else:
            self.send("error")
            print("该文件夹下无文件!!")
            self.handle()

    def uploading(self):
        """
        用户上传功能
        :return:
        """
        disk = input("请输入您要选择的盘符:").strip()
        disk = disk.upper() + ":\\"
        try:
            file_path = self.choice_file(disk, disk)
        except FileNotFoundError:
            print("你输入的磁盘路径有误!!")
            self.uploading()
        else:
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
            self.client.send(num)
            self.client.send(json_bytes.encode())
            # send_size = 0
            with open(file_path, "rb") as f:
                num = self.recv()
                if num == "right":
                    send_size = file_size
                else:
                    send_size = f.seek(int(num))
                    # 断点续传
                while send_size < file_size:
                    read_data = f.read(1024)
                    send_data = self.client.send(read_data)
                    send_size += send_data
                    self.progress(send_size / file_size)
                    # 进度条实现
            ret = self.recv()
            if ret == "right":
                print("文件上传完成!!")
                self.handle()
            else:
                self.uploading()

    def choice_file(self, path, default_path="D:"):
        """
        用户上传文件时选择文件
        :param path: 用户输入的盘符
        :param default_path: 默认盘符
        :return: 用户选择的文件,绝对路径
        """
        list_dir = os.listdir(path)
        for k, v in enumerate(list_dir, 1):
            v = os.path.join(path, v)
            if os.path.isdir(v):
                print(k, v, "文件夹")
            if os.path.isfile(v):
                print(k, v, "文件")
        num = input("请选择序号0返回上一层:")
        if num.isdigit():
            num = int(num)
            if num == 0:
                if path == default_path:
                    print("已经是最顶层了!!")
                    return self.choice_file(path)
                else:
                    upper_path = os.path.dirname(path)
                    return self.choice_file(upper_path)
            if 0 < num < len(list_dir) + 1:
                choice = list_dir[num - 1]
                new_path = os.path.join(path, choice)
                if os.path.isdir(new_path):
                    return self.choice_file(new_path)
                else:
                    return new_path
        else:
            print("请正确输入!!")

    @staticmethod
    def progress(percent, width=100):
        """
        显示进度条函数
        :param percent: 数据百分比
        :param width: 进度条宽度,默认100
        """
        if percent >= 1:
            percent = 1
        print(format(f"\r[{int(width*percent)*'#'}", f"<{width}"), f"] {int(percent*100)}%", end="")


if __name__ == '__main__':
    Client(("127.0.0.1", 10010))
