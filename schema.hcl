# Git Lanes DB スキーマ定義（Atlas 宣言型マイグレーション）
# 適用: atlas schema apply --url 'sqlite://dev.db' --to 'file://schema.hcl' --dev-url 'sqlite://dev?mode=memory'

schema "main" {}

table "repositories" {
  schema = schema.main

  column "id" {
    type = text
    null = false
  }

  column "path" {
    type = text
    null = false
  }

  column "name" {
    type = text
    null = false
  }

  primary_key {
    columns = [column.id]
  }
}
