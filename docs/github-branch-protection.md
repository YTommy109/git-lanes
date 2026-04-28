# GitHub ブランチ保護設定手順

main ブランチへのマージ前に CI が必須通過するよう設定する。
初回セットアップ時に一度だけ GitHub の画面で実施する。

## 手順

1. リポジトリの **Settings** タブを開く
2. 左メニューの **Branches** をクリック
3. **Branch protection rules** セクションの **Add rule** をクリック
4. **Branch name pattern** に `main` と入力して、以下の項目を有効にする:

   | 項目 | 設定 |
   | --- | --- |
   | Require a pull request before merging | ✅ |
   | Require status checks to pass before merging | ✅ |
   | Require branches to be up to date before merging | ✅ |
   | Do not allow bypassing the above settings | ✅ |

   **Status checks** の検索欄で以下の 3 つを追加する（CI が一度でも実行されていれば候補に出る）:

   - `lint-typecheck`
   - `test`
   - `test-e2e`

5. **Create** をクリックして保存する

## 確認方法

設定後、main への PR を作成すると Checks タブに 3 つのジョブが表示される。
すべて ✅ になるまでマージボタンが無効化される。
