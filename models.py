import vk_api
from vk_api.longpoll import VkLongPoll
from vk_config import group_token
from random import randrange
import sqlite3
from os import path, mkdir


seeker_scopes = [
    "bdate",
    "sex",
    "city",
    "relation"
    ]

seeker_info = {
    "bdate": 0,
    "sex": 0,
    "city_id": 0,
    "city": 0,
    "relation": 0
    }

db_path = path.join(f"{path.abspath('db')}", "couple_db.db")

# Для работы с ВК
vk = vk_api.VkApi(token=group_token)
longpoll = VkLongPoll(vk)

# Создание папки для БД
def create_folder():
    if not path.isdir("db"):
        mkdir("db")

# Создание таблиц БД, если их ещё нет
def create_db():
    create_folder()
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user(
            id INTEGER PRIMARY KEY,
            vk_id INTEGER UNIQUE
        );
        """)
        conn.commit()

    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS dating_user(
            id INTEGER PRIMARY KEY,
            vk_id INTEGER UNIQUE,
            first_name VARCHAR(60),
            second_name VARCHAR(60),
            city VARCHAR(60),
            link VARCHAR(140),
            id_user INTEGER REFERENCES user(id) ON DELETE CASCADE
        );
        """)
        conn.commit()

    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS photos(
            id INTEGER PRIMARY KEY,
            link_photo VARCHAR(60),
            count_likes VARCHAR(60),
            id_dating_user INTEGER 
            REFERENCES dating_user(id) ON DELETE CASCADE
        );
        """)
        conn.commit()

    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS black_list(
            id INTEGER PRIMARY KEY,
            vk_id INTEGER UNIQUE,
            first_name VARCHAR(60),
            second_name VARCHAR(60),
            city VARCHAR(60),
            link VARCHAR(140),
            link_photo VARCHAR(250),
            count_likes INTEGER,
            id_user INTEGER REFERENCES user(id) ON DELETE CASCADE
        );
        """)
        conn.commit()


""" 
ФУНКЦИИ РАБОТЫ С БД
"""

# Удаляет пользователя из черного списка
def delete_db_blacklist(ids):
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM black_list WHERE vk_id = ?;
            """, (ids,))
        conn.commit()


# Удаляет пользователя из избранного
def delete_db_favorites(ids):
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM dating_user WHERE vk_id = ?;
            """, (ids,))
        conn.commit()


# Проверят зареган ли пользователь бота в БД
def check_db_master(ids):
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT vk_id FROM user WHERE vk_id = ?;
        """, (ids,))
        res = cur.fetchone()
        if res is None:
            return False
        return res


# Проверят есть ли юзер в бд
def check_db_user(ids):
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT vk_id FROM dating_user WHERE vk_id = ?;
        """, (ids,))
        dating_user = cur.fetchone()

        cur.execute("""
        SELECT vk_id FROM black_list WHERE vk_id = ?;
        """, (ids,))
        blocked_user = cur.fetchone()

    return dating_user, blocked_user


# Проверят есть ли юзер в черном списке
def check_db_black(ids):
    current_users_id = check_db_master(ids)
    # Находим все анкеты из избранного которые добавил данный юзер
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT first_name, second_name, vk_id FROM black_list 
        WHERE id_user = ?;
        """, (current_users_id))
        all_users = cur.fetchall()
    return all_users


# Проверяет есть ли юзер в избранном
def check_db_favorites(ids):
    current_users_id = check_db_master(ids)
    # Находим все анкеты из избранного которые добавил данный юзер
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT first_name, second_name, vk_id FROM dating_user 
        WHERE id_user = ?;
        """, (current_users_id))
        all_users = cur.fetchall()
    return all_users


# Пишет сообщение пользователю
def write_msg(user_id, message, attachment=None):
    random_id = randrange(10 ** 7)
    res = vk.method('messages.send', {
        'user_id': user_id,
        'message': message,
        'random_id': random_id,
        'attachment': attachment
        })
    try:  
        res == random_id
    except Exception:
        print("Не удалось отправить сообщение пользователю")
        print("Смотри write_msg в models")
        return res


# Регистрация пользователя
def register_user(vk_id):
    if check_db_master(vk_id) == False:    
        with sqlite3.connect(f"{db_path}") as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO user(vk_id)
            VALUES (?);
            """, (vk_id,))
            conn.commit()
        write_msg(vk_id, "Вы прошли регистрацию.")
    else:
        write_msg(vk_id, "Вы уже зарегистрированы.")


# Сохранение выбранного пользователя в БД
def add_user(event_id, vk_id, first_name, second_name, city, link, id_user):
    dating_user, blocked_user = check_db_user(vk_id)
    if dating_user == None:
        with sqlite3.connect(f"{db_path}") as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO dating_user(
                vk_id, 
                first_name, 
                second_name, 
                city, 
                link, 
                id_user
                )
            VALUES (?, ?, ?, ?, ?, ?);
            """, (vk_id, first_name, second_name, city, link, id_user))
            conn.commit()
            write_msg(event_id, 'ПОЛЬЗОВАТЕЛЬ УСПЕШНО ДОБАВЛЕН В ИЗБРАННОЕ')
            return True
    else:
        write_msg(event_id, 'Пользователь уже в избранном.')
        return False


# Сохранение в БД фото добавленного пользователя
def add_user_photos(event_id, link_photo, count_likes, id_dating_user):
    with sqlite3.connect(f"{db_path}") as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT id_dating_user FROM photos WHERE id_dating_user = ?;
        """, (id_dating_user,))
        if cur.fetchone() == None:
            cur.execute("""
            INSERT INTO photos(link_photo, count_likes, id_dating_user)
            VALUES (?, ?, ?);
            """, (link_photo, count_likes, id_dating_user))
            conn.commit()
            write_msg(event_id, 'Фото пользователя сохранено в избранном')
            return True
        else:
            write_msg(
                event_id, 
                'Невозможно добавить фото этого пользователя(Уже сохранено)'
                )
            return False


# Добавление пользователя в черный список
def add_to_black_list(event_id, vk_id, first_name, second_name, 
                      city, link, link_photo, count_likes, id_user):
    dating_user, blocked_user = check_db_user(vk_id)
    if blocked_user == None:
        with sqlite3.connect(f"{db_path}") as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO black_list(
                vk_id, 
                first_name, 
                second_name, 
                city, 
                link, 
                link_photo,
                count_likes,
                id_user
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                vk_id, 
                first_name, 
                second_name, 
                city, 
                link, 
                link_photo, 
                count_likes, 
                id_user
                )
            )
            conn.commit()
            write_msg(event_id, 'Пользователь успешно заблокирован.')
            return True
    else:
        write_msg(event_id, 'Пользователь уже в черном списке.')
        return False