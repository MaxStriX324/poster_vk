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
    

#подключение к базе данных
def connect_to_bd():
    try:
        sqlite_connection = sqlite3.connect('dbposter.db')
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

"""def message_to_bd(message, id_user):
    sqlite_connection, cursor = connect_to_bd()
    cur.execute("insert into posts values (?, ?)", ("C", 1972))
    disconect_to_bd(sqlite_connection, cursor)"""

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
    print(r_unixdate)
    cursor.execute('SELECT * FROM posts WHERE PUBLISH_DATE > ?', (r_unixdate, ))
    result = cursor.fetchall()
    disconect_to_bd(sqlite_connection, cursor)
    return(len(result))

def upload_photo_to_album(id_db, cursor):
    vk_sess = vk_api.VkApi(get_settings('login'), get_settings('password'))

    try:
        vk_sess.auth(token_only=True)
    except vk_api.AuthError as error_msg:
        print(error_msg)
        return

    upload = vk_api.VkUpload(vk_sess)
    
    cursor.execute('SELECT ATTACHMENTS FROM posts WHERE ID = ?', (id_db, ))
    path = cursor.fetchall()
    print(path[0][0])
    photo = upload.photo(  # Подставьте свои данные
        path[0][0],
        album_id=275430694,
        group_id=199728158
    )

    vk_photo_url = 'photo{}_{}'.format(
        photo[0]['owner_id'], photo[0]['id']
    )

    #print(photo, '\nLink: ', vk_photo_url)
    print('Фото успешно загружено в альбом')
    cursor.execute("update posts SET PHOTO_URL = (?) WHERE ID = (?)", (vk_photo_url, id_db, ))
    

def add_post_to_bd(id_db, text, from_id, path):
    sqlite_connection, cursor = connect_to_bd()
    cursor.execute("INSERT OR IGNORE into posts values (?, ?, ?, ?, ?, ?, ?, ?, ?)", (id_db, text, 1, 'NULL', 0, 0, 0, from_id, 0, ))
    if path != 0:
        cursor.execute("update posts SET ATTACHMENTS = (?) WHERE ID = (?)", (path, id_db, ))
        upload_photo_to_album(id_db, cursor)
        print('Сообщение удачно записано с фото')
    else:
        cursor.execute("update posts SET FROM_ID = (?) WHERE ID = (?)", (from_id, id_db, ))
        print('Сообщение удачно записано без фото')
 #   if search_datetime_to_bd() != 0:
 #       r_unixdate = int(time.time())
 #       if id_db - 1
        
    sqlite_connection.commit()
    disconect_to_bd(sqlite_connection, cursor)    

    

def main(): 
    vk_session = vk_api.VkApi(token=get_settings('token'))
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, get_settings('group_id'))

    for event in longpoll.listen():     #цикл проверки событий

        if event.type == VkBotEventType.MESSAGE_NEW:        #если событие это новое сообщение
            print('пришло новое сообщение')
            text = event.obj.message['text']
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
                            
                            add_post_to_bd(id_photo, text, from_id, path_to_photo)
                else:
                    add_post_to_bd(id_photo, text, from_id, 0)
                            
                            
                            
                
                try:
                    vk.messages.send(
                    peer_id=get_settings('chat_id'),
                    random_id=get_random_id(),
                    message=text)
                except:
                    print("Ошибка отправки сообщения у id" + str(from_id))
 

        else:
            print(event.type)
            print()


if __name__ == '__main__':
    main()
