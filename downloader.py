import os
import shutil

from requests_html import HTMLSession

DOWNLOAD_DIR = './temp'


def download(source: str) -> bool:
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    if 'cloud.mail.ru' in source:
        return download_mailru(source)
    else:
        print("Еще не поддерживается!")
        return False


def download_mailru(source: str) -> bool:
    session = HTMLSession()
    weblink = source[29:]

    if weblink.endswith("/"):
        weblink = weblink[:-1]

    items_r = session.get("https://cloud.mail.ru/api/v4/public/list?weblink="+weblink)
    links_r = session.get("https://cloud.mail.ru/api/v2/dispatcher", headers={"referer": source})

    if items_r.status_code != 200 | links_r.status_code != 200:
        return False

    items = items_r.json()
    links = links_r.json()

    weblink_get = links.get('body').get('weblink_get')[0].get('url')

    if items.get('type') == "folder":
        item_list = items.get('list')
    else:
        item_list = [items]

    for item in item_list:
        img_link = weblink_get + "/" + item.get('weblink')

        img = session.get(img_link, stream=True)

        if img.status_code == 200:
            img.raw.decode_content = True

            with open(DOWNLOAD_DIR + "/" + item.get("name"), "wb") as f:
                shutil.copyfileobj(img.raw, f)

            print("Файл", item.get("name"), "скачан")
        else:
            print("Ошибка при скачивании", item.get("name"))
            return False

    return True
