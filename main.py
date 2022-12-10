#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime as dt
import os
import re
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
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


def print_log(message: str, level: str) -> None:
    print(f"[{dt.now()}:{level}] {message}")


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


def download_file(url: str, path: str) -> bool:
  """ファイルをダウンロードする
  -----
  url
    ファイルのURL
  
  path
    保存先のパス名

  return
    True: 成功
    False: 失敗
  """

  # ファイルをダウンロード
  try:
    sleep(0.2)  # 403対策
    response = requests.get(url)
    print_log(f"GET [{url}]", LogLebel.INFO)

  except:
    print_log(f"GET FAILED [{url}]", LogLebel.ERROR)
    return False

  if not response.ok:
    print_log(f"BAD STATUS [{response.status_code}]", LogLebel.WARNING)
    return False

  # ファイルを保存
  try:
    bytes = io.BytesIO(response.content)
    image = Image.open(bytes)
    image.save(path)
    print_log(f"SAVE [{path}]", LogLebel.INFO)

  except:
    print_log(f"IO ERROR", LogLebel.ERROR)
    return False
  
  return True


class Result:
  def __init__(self):
    self._titles = {}
    self._done = {}

  @property
  def urls(self):
    return self._titles.keys()

  def save(self, path: str):
    lines = []
    lines.append("done, url, title\n")
    for url in self.urls:
      title = self.title(url)
      done = self.done(url)
      line = f"{done}, {url}, {title}\n"
      lines.append(line)
    with open(path, 'w', encoding='utf-8') as f:
      f.writelines(lines)

  def fail(self, url, title):
    self._titles[url] = title
    self._done[url] = False

  def success(self, url, title):
    self._titles[url] = title
    self._done[url] = True

  def title(self, url):
    return self._titles[url]

  def done(self, url):
    return self._done[url]


def save_thumbnails(
  driver: webdriver.Chrome,
  url: str,
  out_dir: str,
  thumb_url: str = '') -> Result:
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

  return
    ダウンロード結果
  """

  result = Result()

  # HTMLを取得
  try:
    sleep(1)  # 403 Forbidden対策
    driver.get(url)
    print_log(f"GET [{url}]", LogLebel.INFO)

  except:
    print_log(f"GET FAILED [{url}]", LogLebel.ERROR)
    return result
    

  # img要素を取得
  img_list = driver.find_elements(By.TAG_NAME, 'img')

  for img in img_list:
      # 画像URLを取得
      url = img.get_attribute('src')

      # 画像URLが存在しない、または目的のURLでなければスキップ
      if (not url) or (thumb_url and not re.match(thumb_url, url)):
        continue

      # 保存先のファイルパスを取得
      title = img.accessible_name
      _, ext = os.path.splitext(url)
      file_name = title + ext
      file_name = re.sub(r'[\\|/|:|?|"|<|>|\|]', '_', file_name) # 違反文字を_に置換
      path = os.path.join(out_dir, file_name)
      path = get_unduplicate_path(path)

      # 画像をダウンロード
      ok = download_file(url, path)

      # 結果を登録
      if ok:
        result.success(url, title)
      else:
        result.fail(url, title)

  return result


def main(args) -> None:
  # ベースとなるURLを生成
  base_url = SEARCH_URL.format(args.query)

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

  # 開始ページ番号と終了ページ番号を取得
  first_page = args.first_page
  last_page = args.last_page

  # 画像の出力先フォルダを作成
  today = dt.today().strftime('%Y-%m-%d')
  out_dir = os.path.join("out", args.query, today,
                         f"page.{first_page}-{last_page}")
  if (not os.path.exists(out_dir)):
    os.makedirs(out_dir)

  # すべてのページのサムネイル画像を保存する
  for page in range(first_page, last_page + 1):
    page_url = base_url + f"&page={page}"
    result = save_thumbnails(driver, page_url, out_dir, THUMBNAIL_URL)

  # ダウンロードに失敗した画像を再度ダウンロード
  for url in result.urls:
    if (result.done(url)):
      continue
    title = result.title(url)
    _, ext = os.path.splitext(url)
    file_name = title + ext
    file_name = re.sub(r'[\\|/|:|?|"|<|>|\|]', '_', file_name) # 違反文字を_に置換
    path = os.path.join(out_dir, file_name)
    path = get_unduplicate_path(path)
    if download_file(url, path):
      result.success(url, title)

  # ダウンロード結果をファイルに保存
  result.save(os.path.join(out_dir, "result.csv"))


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="TOKYO Motionのサムネイル画像をダウンロードします")
  parser.add_argument("-q", "--query", required=True, help="動画の検索文字列を指定します")
  parser.add_argument("--first-page", help="最初のページ番号を指定します", default=1)
  parser.add_argument("--last-page", help="最後のページ番号を指定します", default=1)
  args = parser.parse_args()
  main(args)
