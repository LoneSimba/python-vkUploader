import json
import vk_api
import getpass

KEY_FILE = 'vk_auth.key'


def auth_vk_password():
    login = input("VK логин: ")
    session = vk_api.VkApi(login=login, password=getpass.getpass("VK пароль: "))
    session.auth()

    with open(KEY_FILE, "w+", encoding='utf-8') as f:
        auth = {
            'login': login,
            'token': session.token.get('access_token')
        }

        f.write(json.dumps(auth))

    return session.get_api()


def auth_vk_token():
    try:
        with open(KEY_FILE, "r", encoding='utf-8') as f:
            token = f.readline()

        if len(token) == 0:
            return auth_vk_password()
        else:
            token_obj = json.loads(token)

            try:
                session = vk_api.VkApi(login=token_obj.get('login'), token=token_obj.get('token'))
                session.auth()
                return session.get_api()
            except vk_api.PasswordRequired as e:
                return auth_vk_password()

    except IOError as e:
        return auth_vk_password()
