import os
import mimetypes
import subprocess

import click
import pygsheets
import vk_api as vk

import auth_vk
import downloader

from datetime import datetime

VK_GROUP = '209413490'
VK_ALBUM = '282016227'

GREEN = (0.8509804, 0.91764706, 0.827451, 0)
GREY = (0.8509804, 0.8509804, 0.8509804, 0)
BLUE = (0.23921569, 0.52156866, 0.7764706, 0)


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

    vk_api = auth_vk.auth_vk_token()
    vk_uploader = vk.upload.VkUpload(vk_api)
    g_api = pygsheets.authorize(service_file='service_secret.json')
    sheet = g_api.open('Копия 2022"Оценочные листы "Я открываю книгу" 2022"')

    worksheet = sheet.sheet1
    rows = worksheet.get_values(start=(start, 1), end=(end, 17), returnas='cell')

    row: list[pygsheets.Cell]
    for row in rows:
        if is_cells_colored(row):
            print("Работа с номером", row[0].value_unformatted, "отмечена как исключенная, пропускаю")
            continue

        if is_cell_colored(row[12]):
            print("Работа с номером", row[0].value_unformatted, "отмечена как обработанная, пропускаю")
            continue

        if downloader.download(row[15].value_unformatted):
            dir = os.fsencode(downloader.DOWNLOAD_DIR)

            for file in os.listdir(dir):
                filename = os.fsdecode(file)
                path = downloader.DOWNLOAD_DIR + "/" + filename
                (mime, _) = mimetypes.guess_type(filename)

                if "image" not in mime:
                    print("Ошибка: %s не является изображением (%s)! Пропускаю" % (filename, mime))
                    continue
                elif not (("gif" in mime) or ("jpeg" in mime) or ("png" in mime)):
                    # subprocess.call("heic2jpeg -s " + path + " --keep")
                    print("Ошибка: не поддерживаемый формат изображения (Ожидаются: gif, jpeg/jpg, png) у файла ",
                          filename, "! Пропускаю")
                    continue

                caption = "\"%s\". %s\n" % (row[12].value_unformatted, row[13].value_unformatted)
                caption += "Автор - %s, %s лет.\n" % (row[5].value_unformatted, row[6].value_unformatted)
                caption += "Педагог - %s\n" % row[9].value_unformatted
                caption += "%s, %s" % (row[2].value_unformatted, row[3].value_unformatted)
                caption += "\n\nfile: %s" % filename

                if vk_uploader.photo(path, VK_ALBUM, None, None, caption, None, VK_GROUP):
                    os.remove(path)
                    print("Изображение", filename, "загружено!")

        else:
            print("Не удалось скачать работу с номером", row[0].value_unformatted)


# Проверка закрашенности массива ячеек
def is_cells_colored(cells: list[pygsheets.Cell]) -> bool:
    for cell in cells:
        if cell.color != GREY:
            return False

    return True


def is_cell_colored(cell: pygsheets.Cell) -> bool:
    return cell.color == GREY or cell.color == BLUE or cell.color == GREEN


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