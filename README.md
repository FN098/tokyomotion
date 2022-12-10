# TOKYO Motion - 動画サムネイル画像一括保存ツール

## launch.json

```json
{
  "version": "0.2.0",
  "configurations": [
  
    {
      "name": "サムネ一括保存",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "args": ["-q", "ライブチャット"],
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

## 参考

[【Python3】Seleniumで画像を保存する方法](https://senablog.com/python-selenium-image-save/)

[Python 同じ名前のファイルが在ればリネームする。](https://qiita.com/mareku/items/d29fc9bd46f40264d815)

[Seleniumで広告をブロックし読み込みを速くする【selenium-wire】](https://www.zacoding.com/post/selenium-ad-block/)

[Pythonでコマンドライン引数を受け取る](https://qiita.com/taashi/items/07bf75201a074e208ae5)

[PythonでURLからファイル名を取得してみる](https://alicehimmel.hatenadiary.org/entry/20101121/1290316337)

[［解決！Python］argparseモジュールを使ってコマンドライン引数を処理するには](https://atmarkit.itmedia.co.jp/ait/articles/2201/11/news031.html)

[Pythonに訪れる型のある世界](https://www.w2solution.co.jp/tech/2022/04/14/python%E3%81%AB%E8%A8%AA%E3%82%8C%E3%82%8B%E5%9E%8B%E3%81%AE%E3%81%82%E3%82%8B%E4%B8%96%E7%95%8C/#:~:text=%E3%82%A2%E3%83%8E%E3%83%86%E3%83%BC%E3%82%B7%E3%83%A7%E3%83%B3%E3%81%A8%E3%81%84%E3%81%86%E8%A8%80%E8%91%89%E3%81%AF%E3%80%81%E3%80%8C%E6%B3%A8%E9%87%88,%E3%81%A8%E3%81%84%E3%81%86%E3%81%93%E3%81%A8%E3%81%AB%E3%81%AA%E3%82%8A%E3%81%BE%E3%81%99%E3%80%82)
