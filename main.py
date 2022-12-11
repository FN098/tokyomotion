#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime as dt
import os
import re
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import io
from PIL import Image
import argparse


BASE_URL = "https://www.tokyomotion.net/search?search_type=videos&type=public"
THUMBNAIL_URL = "https://cdn.tokyo-motion.net/media/videos"
LOG_FILE_NAME = "download.log"
U_BLOCK_ORIGIN_PATH = os.path.join(os.getenv(
    'LOCALAPPDATA'), r"Google\Chrome\User Data\Profile 1\Extensions\cjpalhdlnbpafiamejdnhcphjbkeiagm\1.45.2_0")


# 現在のサムネイル画像番号
g_file_index = 1

# 保存を試みたファイル総数
g_total_count = 0

# 保存したファイル数
g_saved_count = 0


class LogLebel:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Log:
    _file = None

    @classmethod
    def open(cls, file):
      cls._file = open(file, mode="w", encoding="utf-8")

    @classmethod
    def close(cls):
      cls._file.close()

    @classmethod
    def print(cls, object, level=LogLebel.INFO):
      message = f"[{dt.now()}:{level}] {object}" + "\n"
      if cls._file:
        cls._file.write(message)
        cls._file.flush()
      else:
        print(message)


def get_unduplicate_path(path: str) -> str:
    """重複しないパス名を取得
    ---
    path
      元になるパス名

    return
      重複しなかった場合は元のパス名、重複した場合は末尾に(数字)が付いたパス名
    """

    dst_path = path
    for i in range(2, 999):
      if os.path.exists(dst_path):
          # フルパスから「フルパスタイトル」と「拡張子」を分割
          title, ext = os.path.splitext(dst_path)

          # タイトル末尾に(~)が在れば削除する。
          new_title = re.sub(r'\(.+\)$', "", title)

          # フルパスタイトル + (n) + 拡張子のファイル名を作成
          dst_path = f"{new_title}({i}){ext}"

      else:
          return dst_path

    raise Exception("適切なパス名を取得できません")


def download_file(url: str, path: str) -> None:
  """ファイルをダウンロードする
  -----
  url
    ファイルのURL
  
  path
    保存先のパス名
  """

  # ファイルをダウンロード
  response = requests.get(url)
  if not response.ok:
    raise Exception(f"BAD STATUS [{response.status_code}]")

  # ファイルを保存
  bytes = io.BytesIO(response.content)
  image = Image.open(bytes)
  image.save(path)


def save_thumbnails(
        driver: webdriver.Chrome,
        img_url: str,
        out_dir: str,
        thumb_url: str = '',
        with_title: bool = False) -> None:
  """Webページ上のサムネイル画像を保存する
  -----
  driver
    seleniumのChromeドライバ

  url
    WebページのURL
  
  out_dir
    保存先のディレクトリ名

  thumb_url
    サムネイル画像URLの正規表現パターン

  with_title
    ファイル名にタイトル追加
  """

  global g_file_index, g_total_count, g_saved_count

  # HTML
  try:
    Log.print(f"GET \"{img_url}\"", LogLebel.INFO)
    sleep(0.2)  # 403対策
    driver.get(img_url)
  except TimeoutException as e:
    Log.print(e, LogLebel.ERROR)
    return

  # 画像要素
  img_list = driver.find_elements(By.TAG_NAME, 'img')
  for img in img_list:
      # 画像URL
      img_url = img.get_attribute('src')

      # 対象外の画像は無視
      if (not img_url) or (thumb_url and not re.match(thumb_url, img_url)):
        continue

      # 拡張子
      _, ext = os.path.splitext(img_url)

      # 動画リンク
      link = img.find_element(By.XPATH, '../..').get_attribute('href')

      # 動画タイトル
      title = img.get_attribute('title')

      # ファイル名
      if with_title:
        extra = re.sub(r'[\\|/|:|?|*|"|<|>|\|]',
                           '_', title)  # 違反文字を_に置換
      else:
        extra = ''
      file_name = f"{g_file_index}_{extra}{ext}"

      # ファイルパス
      file_path = os.path.join(out_dir, file_name)
      file_path = get_unduplicate_path(file_path)

      # 画像ファイル
      Log.print(f"GET \"{img_url}\"", LogLebel.INFO)
      try:
        g_total_count += 1
        sleep(0.2)  # 403対策
        download_file(img_url, file_path)
        Log.print(f"SAVE \"{file_path}\" <{link}>", LogLebel.INFO)
        g_file_index += 1
        g_saved_count += 1
      except Exception as e:
        Log.print(e, LogLebel.ERROR)


def main(args) -> None:
  # コマンドライン引数
  search_query = args.search_query
  order_by = args.order_by
  start_page = int(args.start_page)
  end_page = int(args.end_page)
  headless = args.headless
  with_title = args.with_title

  # Chrome起動オプション
  options = webdriver.ChromeOptions()
  if headless:
    options.add_argument('--headless')  # ウィンドウ非表示
  options.page_load_strategy = "eager"  # DOM構築後すぐにダウンロード
  options.add_argument(f'load-extension={U_BLOCK_ORIGIN_PATH}')  # uBlock Origin拡張機能

  # Chrome起動
  driver = webdriver.Chrome(options=options)

  # 出力先フォルダ
  dir_name = dt.today().strftime('%Y-%m-%d')
  out_dir = os.path.join("out", dir_name)
  out_dir = get_unduplicate_path(out_dir)
  if (not os.path.exists(out_dir)):
    os.makedirs(out_dir)

  # ログファイル作成
  log_file = os.path.join(out_dir, LOG_FILE_NAME)
  Log.open(log_file)
  print(f'create "{log_file}"')

  # URL作成
  base_url = BASE_URL
  if search_query:
    base_url += f"&search_query={search_query}"
  if order_by:
    base_url += f"&o={order_by}"

  # サムネイル保存
  for page in range(start_page, end_page + 1):
    page_url = base_url + f"&page={page}"
    print(f'chrawling <{page_url}>')
    save_thumbnails(driver, page_url, out_dir, THUMBNAIL_URL, with_title)

  # Chrome終了
  driver.quit()

  # ログファイル終了
  Log.print(f"DOWNLOAD {g_saved_count} of {g_total_count} FILES")
  Log.close()

  # 終了
  print("done!")
  return


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="TOKYO Motionのサムネイル画像をダウンロードします")
  parser.add_argument("-q", "--search-query", help="検索文字列", required=True)
  parser.add_argument("-s", "--start-page", help="開始ページ番号", default=1)
  parser.add_argument("-e", "--end-page", help="終了ページ番号", default=1)
  parser.add_argument(
      "-o", "--order-by", help="ソート順 (bw:再生日時, mr:アップロード時間, mv:閲覧回数, md:コメント数, tr:人気, tf:お気に入り, lg:再生時間", default=None)
  parser.add_argument("--headless", help="ブラウザ非表示", action="store_true")
  parser.add_argument("--with-title", help="ファイル名に動画タイトルを追加", action="store_true")

  args = parser.parse_args()
  main(args)
