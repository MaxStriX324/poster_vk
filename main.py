import sqlite3
import time
import configparser
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import requests
import urllib.request


def get_settings(param):    #функция чтения параметров из конфига
    config = configparser.ConfigParser()  # создаём объекта парсера
    config.read("settings.ini")  # читаем конфиг

    if param == 'login':
        return(config["VK"]["username"])
    elif param == 'password':
        return(config["VK"]["password"])
    elif param == 'token':
        return(config["VK"]["group_token"])
    elif param == 'group_id':
        return(config["VK"]["group_id"])
    elif param == 'album_id':
        return(config["VK"]["album_id"])
    elif param == 'chat_id':
        return(config["VK"]["chat_id"])
    elif param == 'user_id1':
        return(int(config["VK"]["user_id1"]))
    elif param == 'user_id2':
        return(int(config["VK"]["user_id2"]))
    elif param == 'path_to_photo':
        return(config["VK"]["path_to_photo"])
    elif param == 'time':
        return(config["VK"]["time_beth_post"])
    elif param == 'path_to_bd':
        return(config["VK"]["path_to_bd"])    
    

#подключение к базе данных
def connect_to_bd():
    try:
        sqlite_connection = sqlite3.connect(get_settings('path_to_bd'))
        cursor = sqlite_connection.cursor()
        print("База данных успешно подключена к SQLite")
        
    except sqlite3.Error as error:
        print("Ошибка при подключении к sqlite", error)
    return(sqlite_connection, cursor)
    
def disconect_to_bd(sqlite_connection, cursor):
    cursor.close()
    if (sqlite_connection):
        sqlite_connection.close()
        print("Соединение с SQLite закрыто")

def get_old_id_in_db():
    sqlite_connection, cursor = connect_to_bd()
    cursor.execute("SELECT ID FROM posts")
    result = len(cursor.fetchall())
    disconect_to_bd(sqlite_connection, cursor)
    print('последний ID: ' + str(result))
    return(result)

def search_datetime_to_bd():
    sqlite_connection, cursor = connect_to_bd()
    r_unixdate = int(time.time())
    cursor.execute('SELECT * FROM posts WHERE PUBLISH_DATE > ?', (r_unixdate, ))
    result = cursor.fetchall()
    disconect_to_bd(sqlite_connection, cursor)
    return(len(result))

def upload_photo_to_album(id_db, cursor, vk_sess):

    upload = vk_api.VkUpload(vk_sess)
    
    cursor.execute('SELECT ATTACHMENTS FROM posts WHERE ID = ?', (id_db, ))
    path = cursor.fetchall()
    photo = upload.photo(  
        path[0][0],
        album_id=get_settings('album_id'),
        group_id=get_settings('group_id')
    )

    vk_photo_url = 'photo{}_{}'.format(
        photo[0]['owner_id'], photo[0]['id']
    )

    print('Фото успешно загружено в альбом')
    cursor.execute("update posts SET PHOTO_URL = (?) WHERE ID = (?)", (vk_photo_url, id_db, ))
    

def add_post_to_bd(id_db, text, from_id, path, vk_sess):
    sqlite_connection, cursor = connect_to_bd()
    cursor.execute("INSERT OR IGNORE into posts values (?, ?, ?, ?, ?, ?, ?, ?, ?)", (id_db, text, 1, 'NULL', 0, 0, 0, from_id, 0, ))
    if path != 0:
        cursor.execute("update posts SET ATTACHMENTS = (?) WHERE ID = (?)", (path, id_db, ))
        upload_photo_to_album(id_db, cursor, vk_sess)
        print('Сообщение удачно записано с фото')
    else:
        cursor.execute("update posts SET FROM_ID = (?) WHERE ID = (?)", (from_id, id_db, ))
        print('Сообщение удачно записано без фото')
        
    r_unixdate = int(time.time())
    if search_datetime_to_bd() == 0:
        date = r_unixdate + int(get_settings('time'))
        cursor.execute("update posts SET PUBLISH_DATE = (?) WHERE ID = (?)", (date, id_db, ))
    else:
        last_post = id_db - 1
        cursor.execute('SELECT * FROM posts WHERE ID = ?', (last_post, ))
        data = cursor.fetchall()
        date = int(data[0][4]) + int(get_settings('time'))
        cursor.execute("update posts SET PUBLISH_DATE = (?) WHERE ID = (?)", (date, id_db, ))

    sqlite_connection.commit()
    disconect_to_bd(sqlite_connection, cursor)

def send_message_to_user(vk, id_db, type_event, id_user, text, post_id):
    if type_event == 0:
        print("Отправляю сообщение пользователю")
        sqlite_connection, cursor = connect_to_bd()
        cursor.execute('SELECT * FROM posts WHERE ID = ?', (id_db, ))
        data = cursor.fetchall()
        date = time.ctime(int(data[0][4]))
        message_vk = "Пост успешно добавлен в очередь\nТекст поста: " + str(data[0][1]) + "\nСсылка на фото: " + str(data[0][8]) + "\nБудет опубликован: " + str(date) + "\nКоличество отложенных записей(Если больше 150, лучше не писать): " + str(search_datetime_to_bd())
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except:
            print("Ошибка отправки сообщения у id" + str(data[0][7]))    
        disconect_to_bd(sqlite_connection, cursor)

    elif type_event == 1:
        print("Отправляю сообщение пользователю")
        message_vk = "Пользователь подписался на сообщество: \nvk.com/id" + str(id_user)
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except:
            print("Ошибка отправки сообщения")

    elif type_event == 2:
        print("Отправляю сообщение пользователю")
        message_vk = "Пользователь отписался от сообщества: \nvk.com/id" + str(id_user)
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except:
            print("Ошибка отправки сообщения")
            
    elif type_event == 3:
        print("Отправляю сообщение пользователю")
        message_vk = "Пользователь написал коментарий: vk.com/id" + str(id_user) + "\nТекст: " + text + '\nСсылка на пост: vk.com/knkd324?w=wall-' + str(get_settings('group_id')) + '_' + str(post_id)
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except:
            print("Ошибка отправки сообщения")

    elif type_event == 4:
        print("Отправляю сообщение пользователю")
        message_vk = "Количество отложенных записей: " + str(search_datetime_to_bd())
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except:
            print("Ошибка отправки сообщения")
            
    elif type_event == 5:
        print("Отправляю сообщение пользователю")
        message_vk = "Количество отложенных записей: " + str(search_datetime_to_bd()) + '\nСообщение не добавлено в очередб постов((('
        try:
            vk.messages.send(
            peer_id=get_settings('chat_id'),
            random_id=get_random_id(),
            message=message_vk)
        except vk_api.exceptions.ApiError as error:
            print("Ошибка отправки сообщения")
            print(error)

def create_post_vk(vk_session, id_db, vk1):
    try:
        sqlite_connection, cursor = connect_to_bd()
        cursor.execute('SELECT * FROM posts WHERE ID = ?', (id_db, ))
        data = cursor.fetchall()
        vk = vk_session.get_api()
        owner_id_str = '-' + str(get_settings('group_id'))
        result = vk.wall.post(owner_id=owner_id_str, message=data[0][1], from_group=1, attachments=data[0][8], publish_date=data[0][4])
        cursor.execute("update posts SET POST_ID = (?) WHERE ID = (?)", (result['post_id'], id_db, ))
        sqlite_connection.commit()
        print('Пост успешно добавлен в отложенные')
        disconect_to_bd(sqlite_connection, cursor)
    except vk_api.exceptions.ApiError as error_msg:
        print(error_msg)
        print()
        print()
        send_message_to_user(vk1, 0, 5, 0, 0, 0)  

def connect_to_vk():
    vk_sess = vk_api.VkApi(get_settings('login'), get_settings('password'))

    try:
        vk_sess.auth(token_only=True)
    except vk_api.AuthError as error_msg:
        print(error_msg)
        return
    
    vk_session = vk_api.VkApi(token=get_settings('token'))
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, get_settings('group_id'))
    return(vk_sess, vk_session, vk, longpoll)

def bot_msg():
    vk_sess, vk_session, vk, longpoll = connect_to_vk()

    try:
        for event in longpoll.listen():     #цикл проверки событий
            print('Новое событие')

            if event.type == VkBotEventType.MESSAGE_NEW:        #если событие это новое сообщение
                print('пришло новое сообщение')
                
                #Для отладки(ID беседы) искать в конце peer_id
                #print(event.obj)
                
                text = event.obj.message['text']
                print(text)
                if text == 'тест' or text == 'Тест':
                    print('Пользователь попросил узнать кол-во отложенных записей')
                    send_message_to_user(vk, 0, 4, 0, 0, 0) 
                else:
                    from_id = event.obj.message['from_id']
                    if from_id == get_settings('user_id1') or from_id == get_settings('user_id2'):      #если сообщение пришло от нужных людей
                        atchs = event.object.message['attachments']
                        id_photo = int(get_old_id_in_db()) + 1
                        print("Будет записано с id: " + str(id_photo))
                        if atchs:                                                                       #если в сообщении есть фото
                            for atch in atchs:
                                if atch['type'] == 'photo':
                                    photo = atch['photo']

                                    url = photo['sizes'][-1]['url']
                                    img = urllib.request.urlopen(url).read()
                                    path_to_photo = get_settings('path_to_photo') + str(id_photo) + ".jpg"
                                    out = open(path_to_photo, "wb")
                                    out.write(img)
                                    out.close
                                    print('Фото удачно скачано')
                                    
                                    add_post_to_bd(id_photo, text, from_id, path_to_photo, vk_sess)
                        else:
                            add_post_to_bd(id_photo, text, from_id, 0, vk_sess)
                        create_post_vk(vk_sess, id_photo, vk)
                        send_message_to_user(vk, id_photo, 0, 0, 0, 0)            
                    print()
                    print()
                                
            elif event.type == VkBotEventType.GROUP_JOIN:
                print('Человек вошел в группу')
                print(event.obj['user_id'])
                send_message_to_user(vk, 0, 1, event.obj['user_id'], 0, 0)
                print()
                print()                
                
            elif event.type == VkBotEventType.GROUP_LEAVE:
                print('Человек вышел из группы')
                print(event.obj['user_id'])                
                send_message_to_user(vk, 0, 2, event.obj['user_id'], 0, 0)
                print()
                print()
                
            elif event.type == VkBotEventType.WALL_REPOST:
                print('Человек сделал репост')
                print(event.obj)
                print()
                print()

            elif event.type == VkBotEventType.WALL_REPLY_NEW:
                print('Человек написал коментарий')
                send_message_to_user(vk, 0, 3, event.obj['from_id'], event.obj['text'], event.obj['post_id'])
                print()
                print()                
                
            else:
                print(event.type)
                print()
    except requests.exceptions.ReadTimeout:
        print("\n Переподключение к серверам ВК \n")
        time.sleep(60)

def main():
    print('Программа запущена')
    while True:
        bot_msg()

if __name__ == '__main__':
    main()
