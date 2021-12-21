import os
import re
import shutil
import requests

import yadisk
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

DOWNLOAD_DIR = './temp'


def download(source: str, args) -> bool:
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    if 'cloud.mail.ru' in source:
        return download_mailru(source)
    if 'disk.yandex' in source or 'yadi.sk' in source:
        return download_yadisk(source)
    if 'drive.google.com' in source:
        return download_gdrive(source, args)
    else:
        print("Еще не поддерживается:", source)
        return False


def download_mailru(source: str) -> bool:
    weblink = source[29:]

    if weblink.endswith("/"):
        weblink = weblink[:-1]

    items_r = requests.get("https://cloud.mail.ru/api/v4/public/list?weblink="+weblink)
    links_r = requests.get("https://cloud.mail.ru/api/v2/dispatcher", headers={"referer": source})

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
        img_name = re.sub(r'[\"?><:\\/|*]', '', item.get("name"))

        if '.jfif' in img_name:
            img_name = img_name.replace('.jfif', '.jpg')

        img = requests.get(img_link, stream=True)

        if img.status_code == 200:
            img.raw.decode_content = True

            with open("%s/%s" % (DOWNLOAD_DIR, img_name), "wb") as f:
                shutil.copyfileobj(img.raw, f)

            print("Файл %s скачан" % img_name)

        else:
            print("Ошибка при скачивании", item.get("name"))
            return False

    return True


def download_yadisk(source: str) -> bool:
    disk = yadisk.YaDisk()

    links = source.split(' ')

    for link in links:
        data: yadisk.objects.PublicResourceObject
        data = disk.get_public_meta(link)

        items = []
        if data.type == "dir":
            items = data.embedded.items
        else:
            items = [data]

        item: yadisk.objects.PublicResourceObject
        for item in items:
            if item.type == "dir":
                continue

            file = requests.get(item.file, stream=True)
            img_name = re.sub(r'[\"?><:\\/|*]', '', item.name)

            if '.jfif' in img_name:
                img_name = img_name.replace('.jfif', '.jpg')

            if file.status_code == 200:
                file.raw.decode_content = True

                with open("%s/%s" % (DOWNLOAD_DIR, img_name), "wb") as f:
                    shutil.copyfileobj(file.raw, f)

                print("Файл %s скачан" % img_name)

            else:
                print("Ошибка при скачивании", item.name)
                return False

    return True


def download_gdrive(source: str,  drive: GoogleDrive) -> bool:
    items = []
    source_i = re.sub(r'(\?\w+\W+\w+)', '', source)
    if "file/d/" in source:
        fid = re.findall(r'd/([0-9a-z_-]+)', source_i, re.IGNORECASE)[0]
        file_obj = drive.CreateFile({'id': fid})
        file_obj.FetchMetadata(fetch_all=True)
        items = [file_obj]
    elif "folders/" in source:
        fid = re.findall(r'folders/([0-9a-z_-]+)', source_i, re.IGNORECASE)[0]
        items = drive.ListFile({'q': "'%s' in parents" % fid}).GetList()

    item: GoogleDriveFile
    for item in items:
        try:
            img_name = re.sub(r'[\"?><:\\/|*]', '', item.metadata.get('originalFilename'))

            if '.jfif' in img_name:
                img_name = img_name.replace('.jfif', '.jpg')

            item.GetContentFile("%s/%s" % (DOWNLOAD_DIR, img_name))
            print("Файл %s скачан" % img_name)
        except Exception as e:
            print("Ошибка при скачивании", item.metadata.get('originalFilename'))
            return False

    return True
