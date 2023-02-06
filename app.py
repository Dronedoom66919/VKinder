from time import sleep
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_functions import (
    search_users, get_photo, json_create, users_get, 
    sort_likes)
from models import (
    create_db, write_msg, register_user, add_user, add_user_photos, 
    add_to_black_list, check_db_user, check_db_black, check_db_favorites, 
    check_db_master, delete_db_blacklist, delete_db_favorites, seeker_info, 
    seeker_scopes)
from vk_config import group_token, user_token


# Для работы с вк_апи
vk = vk_api.VkApi(token=group_token)
seeker = vk_api.VkApi(token=user_token)
longpoll = VkLongPoll(vk)


def loop_bot():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                message_text = event.text
                return message_text, event.user_id


def menu_bot(id_num):
    write_msg(
        id_num,
        "Вас приветствует бот - Vkinder\n"
        "\nЕсли вы используете его первый раз - пройдите регистрацию.\n"
        "Для регистрации введите - Да.\n"
        "Если вы уже зарегистрированы - начинайте поиск.\n"
        "\nДля поиска - Начать поиск\n"
        "Перейти в избранное нажмите - 2\n"
        "Перейти в черный список - 0\n"
    )


def show_info():
    write_msg(user_id, "Это была последняя анкета.\nМеню бота - Vkinder")     


def reg_new_user(id_num):
    create_db()
    register_user(id_num)
    write_msg(id_num, "Vkinder - для активации бота\n")
    

def check_if_last_record(i, result):
    # Проверка на последнюю запись
    if i >= len(result) - 1:
        show_info()
        return True


def go_to_favorites(ids):
    alls_users = check_db_favorites(ids)
    write_msg(ids, f'Избранные анкеты:')
    for nums, users in enumerate(alls_users):
        write_msg(
            ids, 
            f'{users[0]} {users[1]}, https://vk.com/id{users[2]}'
        )
        write_msg(ids, '1 - Удалить из избранного, 0 - Далее\nq - Выход')
        msg_texts, user_ids = loop_bot()
        if msg_texts == '0':
            if nums >= len(alls_users) - 1:
                show_info()
        # Удаляем запись из бд - избранное
        elif msg_texts == '1':
            delete_db_favorites(users[2])
            write_msg(user_ids, f'Анкета успешно удалена.')
            if nums >= len(alls_users) - 1:
                show_info()
        elif msg_texts.lower() == 'q':
            write_msg(ids, 'Vkinder - для активации бота.')
            break


def go_to_blacklist(ids):
    all_users = check_db_black(ids)
    write_msg(ids, f'Анкеты в черном списке:')
    for num, user in enumerate(all_users):
        write_msg(ids, f'{user[0]} {user[1]}, https://vk.com/id{user[2]}')
        write_msg(ids, '1 - Удалить из черного списка, 0 - Далее \nq - Выход')
        msg_texts, user_ids = loop_bot()
        if msg_texts == '0':
            if num >= len(all_users) - 1:
                show_info()
        # Удаляем запись из бд - черный список
        elif msg_texts == '1':
            delete_db_blacklist(user[2])
            write_msg(user_ids, f'Анкета успешно удалена')
            if num >= len(all_users) - 1:
                show_info()
        elif msg_texts.lower() == 'q':
            write_msg(ids, 'Vkinder - для активации бота.')
            break


def check_bdate():
    # Проверяем корректность даты рождения. 
    date, user_id = loop_bot()
    try:
        date = int(date)
    except ValueError:
        write_msg(
            user_id, 
            "Введите полный год рождения в формате ГГГГ"
            )
        date = check_bdate()
    
    if date not in range(1900, 2023):
        write_msg(
            user_id, 
            "Введите адекватный (1900-2022) год рождения в формате ГГГГ"
            )
        date = check_bdate()

    return date


def check_sex():
    # Проверяем корректность пола.
    sex, user_id = loop_bot()
    if sex in ["2", "мужской", "парень", "мужик", "муж", "м", "мужчина"]:
        sex = "1"
    elif sex in ["1", "женский", "женщина", "девушка", "девочка"]:
        sex = "2"
    else:
        write_msg(user_id, "Введите пол:\n1 - женский\n2 - мужской")
        sex = check_sex()
    return sex


def get_city(city):
    # Находим id города по его названию
    res = seeker.method("database.getCities", {"q": city,})
    try:
        res_items = res['items']
    except KeyError:
        print("Отвалился метод get_city из app")
        return res_items
    return res


def get_city_info():
    # Повторно спрашиваем пользователя при неправильном вводе про город.      
    city, user_id = loop_bot()
    res = get_city(city)
    if res["count"] == 0:
        write_msg(
            user_id, 
            "Похоже такого города ВК не знает, \
            попробуйте ещё раз или введите соседний город"
            )
        res = get_city_info()
    return res


def check_relation():
    # Проверяем корректность семейного положения. 
    relation, user_id = loop_bot()
    if relation in [str(x) for x in range(9)]:
        return relation
        
    write_msg(
        user_id, 
        "Введите цифру от 0 до 8 включительно, \
        в соответствии с указанными выше"
        )
    relation = check_relation()

    return relation


def check_info_completeness(info, user_id):
    # Проверяем информацию на полноту, и если чего-то не хватает
    # отправляем сообщение, что нужно дополнить в словаре seeker_info.
    for elem in seeker_scopes:
        if elem in info.keys():
            if elem == "bdate":
                if len(info["bdate"].split(".")) < 3:
                    write_msg(
                        user_id, 
                        "Не хватает информации!"
                        )
                    write_msg(
                        user_id, 
                        "Введите полный год рождения (например: 1990)"
                        )
                    seeker_info["bdate"] = check_bdate()
                else:
                    seeker_info["bdate"] = info["bdate"].split(".")[2]

            elif elem == "sex":
                if info.get("sex") == 1:
                    seeker_info["sex"] = 2
                else:
                    seeker_info["sex"] = 1

            elif elem == "city":
                seeker_info["city_id"] = info.get("city").get("id")
                seeker_info["city"] = info.get("city").get("title")

            elif elem == "relation":
                seeker_info["relation"] = info.get("relation")

        else:
            write_msg(user_id, "Не хватает информации!")
            if elem == "bdate":
                write_msg(
                    user_id, 
                    "Введите полный год рождения (например: 1977)"
                    )
                seeker_info["bdate"] = check_bdate()
            
            elif elem == "sex":
                write_msg(
                    user_id, 
                    "Введите пол\n1 - женский\n2 - мужской"
                    )
                seeker_info["sex"] = check_sex()                

            elif elem == "city":
                write_msg(user_id, "Введите город")
                city_info = get_city_info()
                seeker_info["city"] = city_info["items"][0]["title"]
                seeker_info["city_id"] = city_info["items"][0]["id"]

            elif elem == "relation":
                write_msg(
                    user_id, 
                    """Введите cемейное положение:
                    1 — не женат/не замужем
                    2 — есть друг/есть подруга
                    3 — помолвлен/помолвлена
                    4 — женат/замужем
                    5 — всё сложно
                    6 — в активном поиске
                    7 — влюблён/влюблена
                    8 — в гражданском браке
                    0 — не указано"""
                    )
                seeker_info["relation"] = check_relation()
    
    return seeker_info


if __name__ == '__main__':
    while True:
        msg_text, user_id = loop_bot()
        if msg_text.lower() == "vkinder":
            menu_bot(user_id)
            msg_text, user_id = loop_bot()

            # Регистрируем пользователя в БД
            if msg_text.lower() == 'да':
                reg_new_user(user_id)

            # Ищем партнера
            elif msg_text.lower() == 'начать поиск':
                user_info = users_get(user_id)

                # Проверяем чего не хватает
                check_info_completeness(user_info, user_id)
                result = search_users(
                    seeker_info['sex'], 
                    seeker_info['bdate'], 
                    seeker_info['city_id'], 
                    seeker_info['relation']
                    )
                # Записываем анкеты-результаты в json формате
                json_create(result)
                current_user_id = check_db_master(user_id)[0]

                # Производим отбор анкет
                for i in range(len(result)):
                    sleep(0.5)

                    # Проверяем есть ли человек в базе
                    dating_user, blocked_user = check_db_user(result[i][3])
                    if dating_user or blocked_user != None:
                        write_msg(user_id, 'Этого человека уже смотрели')
                        continue

                    # Получаем фото и сортируем по лайкам
                    user_photo = get_photo(result[i][3])
                    if user_photo == (
                        'next' 
                        or dating_user is not None 
                        or blocked_user is not None
                        ):
                        write_msg(user_id, 'Этот человек не подходит')
                        check_if_last_record(i, result)
                        continue

                    # Сортируем фото по лайкам
                    sorted_user_photo = sort_likes(user_photo)

                    # Выводим отсортированные данные по анкетам
                    write_msg(
                        user_id, 
                        f'\n{result[i][0]} {result[i][1]} {result[i][2]}'
                        )
                    write_msg(
                        user_id, 
                        f'фото:',
                        attachment=','.join([
                            sorted_user_photo[-1][1], 
                            sorted_user_photo[-2][1],
                            sorted_user_photo[-3][1]
                            ])
                        )
                    
                    # Ждем пользовательский ввод
                    write_msg(
                        user_id, 
                        """1 - Добавить, 2 - Заблокировать, 0 - Далее
                        q - выход из поиска
                        """
                        )
                    msg_text, user_id = loop_bot()
                    if msg_text == '0':
                        check_if_last_record(i, result)

                    # Добавляем пользователя в избранное
                    elif msg_text == '1':
                        if check_if_last_record(i, result):
                            break

                        # Добавляем анкету в БД
                        try:
                            add_user(
                                user_id, 
                                result[i][3], 
                                result[i][1],
                                result[i][0], 
                                seeker_info['city_id'], 
                                result[i][2], 
                                current_user_id
                                )
                            # Добавляем фото анкеты в БД
                            add_user_photos(
                                user_id, 
                                sorted_user_photo[0][1],
                                sorted_user_photo[0][0], 
                                result[i][3]
                                )
                        except AttributeError:
                            write_msg(
                                user_id, 
                                """Вы не зарегистрировались!
                                Введите Vkinder для перезагрузки бота
                                """
                                )
                            break
                    
                    # Добавляем пользователя в черный список
                    elif msg_text == '2':
                        check_if_last_record(i, result)
                        # Блокируем
                        add_to_black_list(
                            user_id, 
                            result[i][3], 
                            result[i][1],
                            result[i][0], 
                            seeker_info['city_id'], 
                            result[i][2],
                            sorted_user_photo[0][1],
                            sorted_user_photo[0][0], 
                            current_user_id
                        )

                    # Выходим из поиска
                    elif msg_text.lower() == 'q':
                        write_msg(
                            user_id, 
                            'Введите Vkinder для активации бота'
                            )
                        break

            # Переходим в избранное
            elif msg_text == '2':
                go_to_favorites(user_id)

            # Переходим в черный список
            elif msg_text == '0':
                go_to_blacklist(user_id)

        else:
            write_msg(user_id, 'Введите Vkinder для активации бота')