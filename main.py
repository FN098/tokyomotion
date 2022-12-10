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
from selenium.webdriver.chrome.options import Options
import argparse


SEARCH_URL = "https://www.tokyomotion.net/search?search_query={}&search_type=videos&type=public"
THUMBNAIL_URL = "https://cdn.tokyo-motion.net/media/videos"


class LogLebel:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Log:
    _file = None

    @classmethod
    def open(cls, file):
      cls._file = open(file, "w", encoding="utf-8")

    @classmethod
    def close(cls):
      cls._file.close()

    @classmethod
    def print(cls, object, level = LogLebel.INFO):
      message = f"[{dt.now()}:{level}] {object}" + "\n"
      if cls._file:
        cls._file.write(message)
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
    for i in range(9999):
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
        url: str,
        out_dir: str,
        thumb_url: str = '') -> None:
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
  """

  # HTMLを取得
  try:
    Log.print(f"GET [{url}]", LogLebel.INFO)
    sleep(0.2)  # 403対策
    driver.get(url)
    WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located)

  except TimeoutException as e:
    Log.print(e, LogLebel.ERROR)
    return

  # サムネイル画像要素を取得
  img_list = driver.find_elements(By.TAG_NAME, 'img')

  for img in img_list:
      # 画像URL
      url = img.get_attribute('src')

      # 画像URLが存在しない、または目的のURLでなければスキップ
      if (not url) or (thumb_url and not re.match(thumb_url, url)):
        continue

      # 画像ファイル拡張子
      _, ext = os.path.splitext(url)

      # 動画タイトル
      title = img.get_attribute('title')

      # 動画リンク
      link = img.find_element(By.XPATH, '../..').get_attribute('href')

      # 保存先のファイルパスを取得
      file_name = title + ext
      file_name = re.sub(r'[\\|/|:|?|"|<|>|\|]', '_', file_name)  # 違反文字を_に置換
      path = os.path.join(out_dir, file_name)
      path = get_unduplicate_path(path)

      # 画像をダウンロード
      Log.print(f"GET [{url}]", LogLebel.INFO)
      try:
        sleep(0.2)  # 403対策
        download_file(url, path)
        Log.print(f"SAVE [{path}]({link})", LogLebel.INFO)
      except Exception as e:
        Log.print(e, LogLebel.ERROR)


def get_page_list(driver: webdriver.Chrome, url: str) -> list:
  """ページネーションされたページ番号のリストを取得する
  ---
  driver
    seleniumのChromeドライバ

  url
    ページURL

  return
    ページ番号のリスト
  """

  page_list = []

  # HTMLを取得
  try:
    Log.print(f"GET [{url}]", LogLebel.INFO)
    sleep(0.2)  # 403対策
    driver.get(url)
    WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located)

  except TimeoutException as e:
    Log.print(e, LogLebel.ERROR)
    return page_list

  # ページ番号を追加
  li_list = driver.find_element(By.CLASS_NAME, 'pagination').find_elements(By.TAG_NAME, 'li')
  for li in li_list:
      innerText = li.get_attribute("innerText")
      if innerText.isdecimal():
        page_list.append(int(innerText))
        
  return page_list


def main(args) -> None:
  # Chrome起動オプション
  options = Options()
  options.add_argument('--headless')  # ウィンドウ非表示

  # Chrome起動
  driver = webdriver.Chrome(options=options)

  # 広告ブロック
  driver.execute_cdp_cmd('Network.enable', {})
  driver.execute_cdp_cmd('Network.setBlockedURLs', {
      'urls': [
          'js.juicyads.com'
      ]})

  # 出力先フォルダを作成
  today = dt.today().strftime('%Y-%m-%d')
  out_dir = os.path.join("out", today, args.query)
  if (not os.path.exists(out_dir)):
    os.makedirs(out_dir)

  # ログファイルオープン
  log_file = os.path.join(out_dir, "download.log")
  Log.open(log_file)

  # 開始ページ番号と終了ページ番号を取得
  base_url = SEARCH_URL.format(args.query)
  page_list = get_page_list(driver, base_url)
  first_page = min(page_list)
  last_page = max(page_list)

  # すべてのページのサムネイル画像を保存する
  for page in range(first_page, last_page + 1):
    page_url = base_url + f"&page={page}"
    save_thumbnails(driver, page_url, out_dir, THUMBNAIL_URL)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="TOKYO Motionのサムネイル画像をダウンロードします")
  parser.add_argument("-q", "--query", required=True, help="検索文字列")
  args = parser.parse_args()
  main(args)
