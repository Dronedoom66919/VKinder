import vk_api
import json
import datetime
from vk_api.longpoll import VkLongPoll
from vk_config import group_token, user_token, V
from vk_api.exceptions import ApiError
from models import seeker_scopes


# Для работы с ВК
vk = vk_api.VkApi(token=group_token)
seeker = vk_api.VkApi(token=user_token)
longpoll = VkLongPoll(vk)


""" 
ФУНКЦИИ ПОИСКА
"""
# Собирает информацию о пользователе
def users_get(seeker):
    seeker_fields = ",".join(seeker_scopes)
    seeker_info = vk.method(
        "users.get", 
        {
            "user_ids": seeker,
            "fields": seeker_fields,
        })
    
    try:
        seeker_info = seeker_info[0]
    except KeyError:
        print("Отвалился метод users_get из vk_functions")
        return seeker_info

    return seeker_info


# Ищет людей по критериям
def search_users(sex, bdate, city, relation):
    all_persons = []
    link_profile = 'https://vk.com/id'
    response = seeker.method(
        'users.search',
        {
            'sort': 1,
            'sex': sex,
            'status': relation,
            'birth_year': bdate,
            'has_photo': 1,
            'count': 25,
            'city': city
        })

    try:
        response = response['items']
    except KeyError:
        print("Отвалился метод search_users из vk_functions")
        return all_persons

    for element in response:
        person = [
            element['first_name'],
            element['last_name'],
            link_profile + str(element['id']),
            element['id']
        ]
        all_persons.append(person)
    return all_persons
    # return True


# Находит фото людей
def get_photo(user_owner_id):
    # Исключаем падение бота от парсинга закрытого профиля ВК
    users_photos = []
    try:
        response = seeker.method(
            'photos.get',
            {
                'access_token': user_token,
                'v': V,
                'owner_id': user_owner_id,
                'album_id': 'profile',
                'count': 10,
                'extended': 1,
                'photo_sizes': 1,
            })
    except ApiError:
        return 'next' # У этого человека закрытый профиль
    # Проверяем корректность отработки запроса
    try:
        photos_amount = response["count"]
    except KeyError:
        print("Отвалился метод get_photo из vk_functions")
        return users_photos
    
    if photos_amount < 3:
        return 'next' # У этого человека кол-во фото меньше 3
    elif photos_amount > 10:
        photos_amount = 10
    for i in range(photos_amount):
        likes = response['items'][i]['likes']['count']
        owner_id = str(response['items'][i]['owner_id'])
        photo_id = str(response['items'][i]['id'])
        users_photos.append([likes, 'photo' + owner_id + '_' + photo_id])
    return users_photos
    # return True


""" 
ФУНКЦИИ СОРТИРОВКИ, ОТВЕТА, JSON
"""
# Сортируем фото по лайкам, удаляем лишние элементы
def sort_likes(photos):
    result = []
    for element in photos:
        result.append(element)
    return sorted(result)


# JSON file create with result of programm
def json_create(lst):
    today = datetime.date.today()
    today_str = f'{today.day}.{today.month}.{today.year}'
    res = {}
    res_list = []
    for num, info in enumerate(lst):
        res['data'] = today_str
        res['first_name'] = info[0]
        res['second_name'] = info[1]
        res['link'] = info[2]
        res['id'] = info[3]
        res_list.append(res.copy())

    with open("result.json", "a", encoding='UTF-8') as write_file:
        json.dump(res_list, write_file, ensure_ascii=False)

    print(f'Информация о загруженных файлах успешно записана в json файл.')