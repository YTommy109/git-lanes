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
  column "cached_head" {
    type = text
    null = true
  }
  column "synced_at" {
    type = integer
    null = true
  }
  primary_key {
    columns = [column.id]
  }
  index "repositories_path_unique" {
    unique  = true
    columns = [column.path]
  }
}

table "commits" {
  schema = schema.main
  column "hash" {
    type = text
    null = false
  }
  column "short_hash" {
    type = text
    null = false
  }
  column "message" {
    type = text
    null = false
  }
  column "author_name" {
    type = text
    null = false
  }
  column "author_email" {
    type = text
    null = false
  }
  column "committed_at" {
    type = integer
    null = false
  }
  column "repo_id" {
    type = text
    null = false
  }
  primary_key {
    columns = [column.hash]
  }
  foreign_key "commits_repo_fk" {
    columns     = [column.repo_id]
    ref_columns = [table.repositories.column.id]
  }
  index "idx_commits_repo_committed_at" {
    columns = [column.repo_id, column.committed_at]
  }
}

table "commit_parents" {
  schema = schema.main
  column "commit_hash" {
    type = text
    null = false
  }
  column "parent_hash" {
    type = text
    null = false
  }
  column "position" {
    type    = integer
    null    = false
    default = 0
  }
  primary_key {
    columns = [column.commit_hash, column.parent_hash]
  }
  foreign_key "commit_parents_child_fk" {
    columns     = [column.commit_hash]
    ref_columns = [table.commits.column.hash]
  }
  foreign_key "commit_parents_parent_fk" {
    columns     = [column.parent_hash]
    ref_columns = [table.commits.column.hash]
  }
}

table "branches" {
  schema = schema.main
  column "name" {
    type = text
    null = false
  }
  column "tip_hash" {
    type = text
    null = false
  }
  column "is_remote" {
    type    = integer
    null    = false
    default = 0
  }
  column "repo_id" {
    type = text
    null = false
  }
  primary_key {
    columns = [column.name, column.repo_id]
  }
  foreign_key "branches_tip_fk" {
    columns     = [column.tip_hash]
    ref_columns = [table.commits.column.hash]
  }
  foreign_key "branches_repo_fk" {
    columns     = [column.repo_id]
    ref_columns = [table.repositories.column.id]
  }
}
