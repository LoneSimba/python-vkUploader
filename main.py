import os
import mimetypes
import warnings

import click
import pygsheets
import vk_api as vk

import auth_vk
import auth_gd
import downloader

from wand.image import Image
from datetime import datetime

VK_GROUP = '209413490'
VK_ALBUM = '282016227'

GREEN = (0.8509804, 0.91764706, 0.827451, 0)
GREY = (0.8509804, 0.8509804, 0.8509804, 0)
BLUE = (0.23921569, 0.52156866, 0.7764706, 0)
RED = (0.91764706, 0.6, 0.6, 0)
DARK_GREY = (0.8, 0.8, 0.8, 0)


@click.command()
@click.option(
    "--start",
    "-s",
    type=int,
    help="Номер первой строки таблицы в очереди, обязательный",
    required=True
)
@click.option(
    "--end",
    "-e",
    type=int,
    help="Номер последней строки таблицы в очереди",
    required=False,
)
def main(start, end):
    if not end:
        end = start

    mimetypes.add_type("image/heic", "HEIC")

    vk_api = auth_vk.auth_vk_token()
    vk_uploader = vk.upload.VkUpload(vk_api)

    gdrive = auth_gd.auth_gd()

    gs_api = pygsheets.authorize(service_file='service_secret.json')
    sheet = gs_api.open('2022"Оценочные листы "Я открываю книгу" 2022"')

    worksheet = sheet.sheet1
    rows = worksheet.get_values(start=(start, 1), end=(end, 17), returnas='cell')

    uploaded = skipped = failed = 0

    row: list[pygsheets.Cell]
    for row in rows:
        if is_excluded(row):
            print("Работа с номером", row[0].value_unformatted, "отмечена как исключенная или обработанная, пропускаю")
            continue

        if downloader.download(row[15].value_unformatted, gdrive):
            dir = os.fsencode(downloader.DOWNLOAD_DIR)
            files_cnt = 0

            for file in os.listdir(dir):
                filename = os.fsdecode(file)
                path = downloader.DOWNLOAD_DIR + "/" + filename
                (mime, _) = mimetypes.guess_type(filename)

                if not mime:
                    tmp_name = filename.lower()
                    if ".heic" in tmp_name:
                        tmp_name = tmp_name.replace(".heic", ".jpg")
                        tmp_path = downloader.DOWNLOAD_DIR + "/" + tmp_name

                        f = open(tmp_path, "wb")
                        f.close()

                        img = Image(filename=path)
                        img.format = 'jpg'
                        img.save(filename=tmp_path)
                        img.close()

                        os.remove(path)

                        path = tmp_path
                        filename = tmp_name
                        (mime, _) = mimetypes.guess_type(filename)

                if not mime or "image" not in mime:
                    print("Ошибка: %s не является изображением (%s)! Пропускаю" % (filename, mime))
                    skipped += 1
                    os.remove(path)
                    continue
                elif not (("gif" in mime) or ("jpeg" in mime) or ("png" in mime)):
                    print("Ошибка: не поддерживаемый формат изображения (Ожидаются: gif, jpeg/jpg, png) у файла ",
                          filename, "! Пропускаю")
                    skipped += 1
                    os.remove(path)
                    continue

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with Image(filename=path) as img:
                        if img.width > 7000 or img.height > 7000:
                            if img.width > img.height:
                                img.transform(resize='7000x')
                            else:
                                img.transform(resize='x7000')
                            img.save(filename=path)
                            img.close()

                caption = "\"%s\". %s\n" % (row[12].value_unformatted, row[13].value_unformatted)
                caption += "Автор - %s, %s лет.\n" % (row[5].value_unformatted, row[6].value)
                caption += "Педагог - %s\n" % row[9].value_unformatted
                caption += "%s, %s" % (row[2].value_unformatted, row[3].value_unformatted)
                caption += "\n\nfile: %s" % filename

                try:
                    if vk_uploader.photo(path, VK_ALBUM, None, None, caption, None, VK_GROUP):
                        print("Изображение", filename, "загружено!")
                        files_cnt += 1
                except Exception as e:
                    print("Не удалось загрузить изображение %s" % path)
                    failed += 1
                finally:
                    os.remove(path)

            if files_cnt > 0:
                row[12].color = GREY
                uploaded += files_cnt
                print("Работа с номером %s загружена! Изображений: %i" % (row[0].value_unformatted, files_cnt))
            else:
                failed += 1
                print("Не удалось загрузить работу с номером", row[0].value_unformatted, row[15].value_unformatted)

        else:
            failed += 1
            print("Не удалось скачать работу с номером", row[0].value_unformatted)

    print("Обработка завершена! Загружено: %i, Пропущено: %i, Ошибки при скачивании/загрузке: %i" %
          (uploaded, skipped, failed))


def is_excluded(cells: list[pygsheets.Cell]) -> bool:
    return is_cells_colored(cells) or is_cell_colored(cells[12]) or is_repeated(cells)


def is_repeated(cells: list[pygsheets.Cell]) -> bool:
    return "повтор" in cells[16].value_unformatted.lower() or "копия" in cells[16].value_unformatted.lower()


# Проверка закрашенности массива ячеек
def is_cells_colored(cells: list[pygsheets.Cell]) -> bool:
    for cell in cells:
        if cell.color != DARK_GREY:
            return False

    return True


def is_cell_colored(cell: pygsheets.Cell) -> bool:
    return cell.color == GREY or cell.color == BLUE or cell.color == GREEN or cell.color == RED


def calc_age(year: str) -> str:
    current_year = datetime.now().year

    if "-" in year:
        years = year.split("-")
    elif len(year) == 2:
        return year
    else:
        years = [year]

    result = []
    for year_i in years:
        result.append(current_year - int(year_i))

    result.sort()
    return "-".join(list(map(str, result)))


if __name__ == "__main__":
     main()
