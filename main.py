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
    """ログレベル
    """
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def print_log(message: str, level: str) -> None:
    """ログを出力
    """
    print(f"[{dt.now()}:{level}] {message}")


def get_unduplicate_path(src_path: str) -> str:
    """重複しないパス名を取得
    ---
    src_path: str
      元になるパス名

    return: str
      重複しないパス名
      重複を検出した場合は末尾に数字が付きます
    """
    
    dst_path = src_path
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


def download_image(src_url: str, dst_path: str, error_urls: list = []) -> None:
  """画像ファイルをダウンロードする
  -----
  src_url: str
    ダウンロード先の画像のURL
  
  dst_path: str
    保存先のパス名

  error_urls: list = []
    ダウンロードに失敗した画像のURLリスト
  """

  # 画像を取得
  try:
    sleep(0.2)  # 403 Forbidden対策
    response = requests.get(src_url)
    print_log(f"GET [{src_url}]", LogLebel.INFO)

  except:
    print_log(f"GET FAILED [{src_url}]", LogLebel.ERROR)
    error_urls.append(src_url)
    return

  # 取得失敗
  if not response.ok:
    print_log(f"BAD STATUS [{response.status_code}]", LogLebel.WARNING)
    error_urls.append(src_url)
    return

  # 画像を保存
  try:
    bytes = io.BytesIO(response.content)
    image = Image.open(bytes)
    image.save(dst_path)
    print_log(f"SAVE [{dst_path}]", LogLebel.INFO)

  except:
    print_log(f"IO ERROR", LogLebel.ERROR)
    error_urls.append(src_url)
    return


def save_screenshot_image(element: WebElement, dst_path: str) -> None:
  """Web要素のスクリーンショットを保存する
  ---
  element: 
    スクリーンショットを取得するWeb要素

  dst_path: str
    保存先のパス名
  """
  # 画像を保存
  try:
    with open(dst_path, "wb") as f:
      f.write(element.screenshot_as_png)
    print_log(f"SAVE [{dst_path}]", LogLebel.INFO)

  except:
    print_log(f"IO ERROR", LogLebel.ERROR)


def save_thumbnails(
  driver: webdriver.Chrome,
  src_url: str,
  out_dir: str,
  thumb_url: str = '',
  save_screenshot: bool = False,
  error_urls: list = []) -> None:
  """Webページ上のサムネイル画像を保存する
  -----
  driver: webdriver.Chrome
    seleniumのChromeドライバ

  src_url: str
    WebページのURL
  
  out_dir: str
    画像ファイル保存先のディレクトリパス名

  thumb_url: str = ''
    サムネイル画像のURLを判定する正規表現パターン

  save_screenshot: bool = True
    スクリーンショットを保存
    または
    オリジナルの画像をダウンロード

  error_urls: list = []
    ダウンロードに失敗した画像のURLリスト
  """

  # HTMLの取得
  try:
    sleep(1)  # 403 Forbidden対策
    driver.get(src_url)
    print_log(f"GET [{src_url}]", LogLebel.INFO)

  except:
    print_log(f"GET FAILED [{src_url}]", LogLebel.ERROR)
    return
    

  # img要素を取得
  img_list = driver.find_elements(By.TAG_NAME, 'img')

  for img in img_list:
      # src属性を取得
      src_url = img.get_attribute('src')

      # src属性が存在しない、または目的のURLでなければスキップ
      if (not src_url) or (thumb_url and not re.match(thumb_url, src_url)):
        continue

      # 保存先のファイルパスを取得
      _, ext = os.path.splitext(src_url)
      dst_path = os.path.join(out_dir, f"{img.accessible_name}{ext}")
      dst_path = get_unduplicate_path(dst_path)

      # 画像を保存
      if save_screenshot:
        save_screenshot_image(img, dst_path)
      else:
        download_image(src_url, dst_path, error_urls)


def get_page_list(driver: webdriver.Chrome, src_url: str) -> list:
  """ページネーションされたページ番号のリストを取得する
  ---
  driver: webdriver.Chrome
    seleniumのChromeドライバ

  src_url: str
    ページ番号を取得するWebページのURL

  return: list
    ページ番号のリスト
  """

  # HTMLの取得
  try:
    driver.get(src_url)
    print_log(f"GET [{src_url}]", LogLebel.INFO)

  except:
    print_log(f"GET FAILED [{src_url}]", LogLebel.ERROR)
    return []

  # paginationクラス要素を取得
  pagination = driver.find_element(By.CLASS_NAME, 'pagination')
  li_list = pagination.find_elements(By.TAG_NAME, 'li')

  # ページ番号のリストを生成
  page_list = []
  for li in li_list:
      innerText = li.get_attribute("innerText")

      try:
        page = int(innerText)
        page_list.append(page)

      except:
        continue

  return page_list


def main(args) -> None:
  # 引数パラメータを取得
  query = args.query
  save_screenshot = args.save_screenshot

  # ベースとなるURLを生成
  base_url = SEARCH_URL.format(query)

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
  page_list = get_page_list(driver, base_url)
  if len(page_list) > 0:
    (first_page, last_page) = (min(page_list), max(page_list))
  else:
    (first_page, last_page) = (0, 0)

  # 画像の出力先フォルダを作成
  today = dt.today().strftime('%Y-%m-%d')
  out_dir = os.path.join("out", query, today,
                         f"page.{first_page}-{last_page}")
  if (not os.path.exists(out_dir)):
    os.makedirs(out_dir)

  # すべてのページのサムネイル画像を保存する
  error_urls = []
  for page in range(first_page, last_page + 1):
    src_url = base_url + f"&page={page}"
    save_thumbnails(driver, src_url, out_dir, THUMBNAIL_URL, save_screenshot, error_urls)

  # ダウンロードに失敗した画像を再度ダウンロード
  error_urls_to_save = []
  for error_url in error_urls:
    save_thumbnails(driver, error_url, out_dir, THUMBNAIL_URL, save_screenshot, error_urls_to_save)

  # ２回目もダウンロードに失敗したURLをテキストファイルに保存
  text_file = os.path.join(out_dir, "error_urls.txt")
  with open(text_file, 'w') as f:
    f.writelines([f"{url}\n" for url in error_urls_to_save])


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="TOKYO Motionのサムネイル画像をダウンロードします")
  parser.add_argument("-q", "--query", required=True, help="動画の検索文字列を入力します")
  parser.add_argument("--save-screenshot", action="store_true", help="サムネイル画像のスクリーンショットを保存します")
  args = parser.parse_args()
  main(args)
