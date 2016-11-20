import _tkinter
import tkinter as tk
from common.transmission.secure_channel import establish_secure_channel_to_server
from tkinter import messagebox
from common.message import MessageType
from pprint import pprint
from client.memory import user_list
from client.memory import current_user
from tkinter import scrolledtext

import select
import _thread
import datetime
import time


class ChatForm(tk.Frame):
    def refresh_user_list(self):
        selected_user = self.get_selected_user()
        self.online_users.delete(0, tk.END)
        for key, value in user_list.items():
            self.online_users.insert(0, value['nickname'])  # + " (" + str(value['id']) + ")")
        self.online_users.insert(0, '[所有用户]')

        select_index = 0

        if selected_user is not None:
            for i, entry in enumerate(self.online_users.get(0, tk.END)):
                if entry == selected_user['nickname']:
                    select_index = i
                    break

        self.online_users.select_set(select_index)

        return

    def append_to_chat_box(self, message, tags):
        self.chat_box.insert(tk.END, message, tags)
        self.chat_box.update()
        self.chat_box.see(tk.END)

    def insert_system_message(self, message, hide_time=False):
        if hide_time:
            time_message = ''
        else:
            time_message = datetime.datetime.fromtimestamp(
                time.time()
            ).strftime('%Y-%m-%d %H:%M:%S')

        self.append_to_chat_box('[系统消息]  ' + message + ' ' + time_message + ' ' + ' \n',
                                'system')
        return

    def get_selected_user(self):
        if len(self.online_users.curselection()) == 0:
            return None
        index = self.online_users.curselection()[0]
        if index == 0:
            return None
        nickname = self.online_users.get(index)
        try:
            return user_list[list(filter(lambda i: user_list[i]['nickname'] == nickname, user_list))[0]]
        except IndexError:
            return None

    def socket_reader(self):
        while True:
            rlist, wlist, xlist = select.select([self.sc.socket], [self.sc.socket], [])

            if (self.should_exit):
                return

            if len(rlist):
                data = self.sc.recv()
                if data:
                    # pprint(data)

                    if data['type'] == MessageType.server_notification:
                        self.insert_system_message(data['parameters'], True)

                    if data['type'] == MessageType.on_user_online:
                        user_list[data['parameters']['id']] = data['parameters']
                        self.insert_system_message(data['parameters']['nickname'] + ' 已经上线')
                        self.refresh_user_list()

                    if data['type'] == MessageType.on_user_offline:
                        # 新用户还没设置好昵称就关闭，可能会有这种情况
                        if not data['parameters'] in user_list:
                            return
                        self.insert_system_message(user_list[data['parameters']]['nickname'] + ' 已经离线')
                        del user_list[data['parameters']]
                        self.refresh_user_list()

                    if data['type'] == MessageType.on_new_message:
                        user = user_list[data['parameters']['user_id']]
                        nickname = user['nickname']
                        user_id = user['id']
                        # pprint(int(data['parameters']['time']))
                        time = datetime.datetime.fromtimestamp(
                            int(data['parameters']['time']) / 1000
                        ).strftime('%Y-%m-%d %H:%M:%S')

                        self.append_to_chat_box(nickname + "   " + time + '\n  ',
                                                ('me' if current_user['id'] == user_id else 'them'))

                        if len(data['parameters']['message']['target_user_id']):
                            self.append_to_chat_box(
                                '悄悄话(对' + user_list[int(data['parameters']['message']['target_user_id'])][
                                    'nickname'] + '说): ', 'system')

                        message = data['parameters']['message'][
                            'data']
                        self.append_to_chat_box(message + '\n', 'message')

                    if data['type'] == MessageType.chat_history_bundle:
                        pprint(data)
                        for key, value in enumerate(data['parameters']):
                            time = datetime.datetime.fromtimestamp(
                                int(value['time']) / 1000
                            ).strftime('%Y-%m-%d %H:%M:%S')
                            self.append_to_chat_box(value['sender_nickname'] + "   " + time + '\n  ', 'them')
                            message = value['message']['data']
                            self.append_to_chat_box(message + '\n', 'message')
                        self.insert_system_message('以上是历史消息', True)
                else:
                    print('服务器已被关闭')
                    # messagebox.showerror("出错了", "服务器已经被关闭")
                    self.master.destroy()

    def __init__(self, sc, master=None):
        super().__init__(master)
        self.pack()
        self.master = master
        self.sc = sc
        self.master.title("聊天室 - " + current_user['nickname'])
        master.resizable(width=True, height=True)
        master.geometry('660x500')
        master.minsize(460, 300)
        self.create_widgets()
        self.should_exit = False

        _thread.start_new_thread(self.socket_reader, ())

    def send_message(self, _=None):
        message = self.input_text.get()
        if not message:
            return
        selected_user = self.get_selected_user()
        target_user_id = ""
        if selected_user:
            target_user_id = str(selected_user['id'])
        self.sc.send(MessageType.send_message, {'target_user_id': target_user_id, 'data': message})
        self.input_text.set("")
        return 'break'

    def online_users_onselect(self, _):
        selected_user = self.get_selected_user()
        if selected_user is not None and selected_user['id'] == current_user['id']:
            self.insert_system_message('您不能给自己发送悄悄话', True)
            self.online_users.selection_clear(0, tk.END)
            self.online_users.select_set(0)

    def create_widgets(self):
        self.online_users = tk.Listbox(self, height=100, bg='#FFFFF0', exportselection=False)
        self.online_users.pack(side="left", padx=(0, 0), pady=(0, 0))
        self.online_users.bind('<<ListboxSelect>>', self.online_users_onselect)

        self.input_text = tk.StringVar()
        self.input_textbox = tk.Entry(self, width=1000, textvariable=self.input_text)
        self.input_textbox.pack(side="bottom", padx=(0, 0), pady=(0, 0))
        self.input_textbox.bind("<Return>", self.send_message)

        self.chat_box = tk.Text(self, x=0, y=0, bg='#f6f6f6')
        self.chat_box.pack(side="right", fill='both', expand='yes')
        self.chat_box.bind("<Key>", lambda e: "break")
        self.chat_box.tag_config("me", foreground="green", lmargin1='10', spacing1='5')
        self.chat_box.tag_config("them", foreground="blue", lmargin1='10', spacing1='5')
        self.chat_box.tag_config("message", foreground="black", lmargin1='14', lmargin2='14', spacing1='5')
        self.chat_box.tag_config("system", foreground="grey", lmargin1='10', lmargin2='10', spacing1='5',
                                 font=("Times New Roman", 8))