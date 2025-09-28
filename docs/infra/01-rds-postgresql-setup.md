# 01. Aurora PostgreSQL クラスター作成手順書

## 概要

国際データ収集システム用の Aurora PostgreSQL クラスターを作成します。
高可用性と自動スケーリングを重視した構成で、システムの安定性と拡張性を確保します。

## Aurora PostgreSQL を選択する理由

### システム要件との適合性

- **高可用性**: 複数国の並列データ収集で安定性が重要
- **自動スケーリング**: データ量増加に自動対応
- **継続的バックアップ**: ポイントインタイム復旧で データ損失リスク最小化
- **読み取りレプリカ**: Web UI 用の読み取り負荷分散
- **パフォーマンス**: 標準 PostgreSQL の 3 倍の性能

## 前提条件

- AWS Management Console へのアクセス権限
- RDS 作成権限を持つ IAM ユーザー
- VPC、サブネット、セキュリティグループの作成権限

## 手順

### Step 1: AWS Management Console へのアクセス

1. AWS Management Console にログイン
2. リージョンを **オレゴン(us-west-2)** に設定
3. サービス検索で「RDS」を検索してクリック

### Step 2: データベース作成の開始

1. RDS ダッシュボードで「**データベースを作成**」をクリック
2. 作成方法で「**標準作成**」を選択

### Step 3: エンジンオプションの設定

```
エンジンタイプ: Amazon Aurora
エディション: Amazon Aurora PostgreSQL-Compatible Edition
バージョン: Aurora PostgreSQL 15.13 (最新の15.x)
```

**設定理由**: Aurora PostgreSQL 15.x は高性能と高可用性を提供

### Step 4: テンプレートの選択

```
テンプレート: 開発/テスト
```

**設定理由**: コスト最適化された設定が自動適用される

### Step 5: 設定

#### DB クラスター識別子

```
DB クラスター識別子: whisperplanet-international-data-aurora-dev
```

#### 認証情報設定

```
マスターユーザー名: postgres
認証情報管理: Magaged in AWS Secrets Manager
暗号化キー：aws/secretsmanager(default)
```

#### クラスタストレージ設定

```
設定オプション: Aurora Standard
```

### Step 6: インスタンス設定

#### DB インスタンスクラス

```
DB インスタンスクラス: バースト可能クラス
db.t4g.medium (2 vCPU、4 GiB RAM)
```

**設定理由**: Aurora 用の最小推奨インスタンス、ARM64 で高性能・低コスト

### Step 7: 可用性と耐久性

```
マルチAZ展開: Auroraレプリカは作成しない
```

**設定理由**: コスト最適の観点から今回は作成しない。

### Step 8: 接続

#### コンピューティングリソース

```
コンピューティングリソース: EC2コンピューティングリソースに接続しない
```

#### ネットワークタイプ

```
ネットワークタイプ: IPv4
```

#### Virtual Private Cloud (VPC)

```
VPC: デフォルト VPC
DB サブネットグループ: デフォルト
```

#### パブリックアクセス

```
パブリックアクセス: 無効
```

**設定理由**: 開発において DB がパブリックにアクセスされることはない。

#### VPC セキュリティグループ

```
VPC セキュリティグループ: 既存のVPC
VPC セキュリティグループ名: default
```

#### アベイラビリティーゾーン

```
アベイラビリティーゾーン: 指定なし
```

#### 認証局

```
Certificate authority: rds-ca-rsa2048-g1(defalut)
```

#### データベースポート

```
データベースポート: 5432
```

#### リードレプリカ書き込みフォワード

```
Turn on local write forwarding: 無効
```

### Babelfish 設定

```
Turn on Babelfish: 有効
```

### Step 9: データベース認証

```
データベース認証: IAM DB認証
```

### Step 10: モニタリング

#### 基本モニタリング設定

```
Database Insights: 標準
Performance insights: 有効
保有期間: 7日
AWS KMSキー: (default)aws/rds
```

#### 拡張モニタリング設定

```
拡張モニタリング: 有効
OSメトリクス粒度: 60秒
モニタリングロール: default
```

#### ログ出力

```

log exports:
iam-db-auth-error log: 有効
instance log: 有効
PostgreSQL log: 有効
IAM ロール: RDS service-linked role
Turn on Devops Guru: 無効

```

### Step 10: 追加設定

#### データベースオプション

```

DB クラスターパラメータグループ: 新規作成
DB パラメータグループ名: whisperplanet-international-data-param-group

```

#### Babelfish 設定

```

DB 移行モード: Single DB
デフォルト照合ロケール: en-US
照合名: sql_latin1_general_cp1_ci_as
TDS ポート: 1433
DB パラメータグループ: default.aurora-postgresql15
フェールオーバ優先: 指定なし

```

#### バックアップ

```

バックアップ保持期間: 7 日
Copy tags to snapshots: 有効

```

#### 暗号化

```

保存時の暗号化: 有効
AWS KMS キー: (デフォルト) aws/rds

```

#### メンテナンス

```

自動マイナーバージョンアップグレード: 有効
メンテナンスウィンドウ: 指定なし (AWS が選択)
削除保護: 無効

```

**設定理由**: 開発環境のため削除を容易にする

### Step 11: 月間推定コスト確認

作成前に右側の「月間推定コスト」を確認

- 予想コスト: 約 $90-100/月 (db.t4g.medium + レプリカ不使用時)
- **注意**: Aurora は高機能だが、RDS より高コスト

### Step 12: データベース作成実行

1. 「**データベースを作成**」をクリック
2. 作成開始の確認メッセージが表示される
3. 作成完了まで約 15-20 分待機（クラスター + レプリカ作成のため）

## 作成完了後の設定

Aurora クラスターに接続するため、デフォルトセキュリティグループにインバウンドルールを追加します。

#### 13-1: セキュリティグループの確認

1. RDS ダッシュボードで作成したクラスターをクリック
2. 「接続とセキュリティ」タブで「VPC セキュリティグループ」を確認
3. セキュリティグループ ID（sg-xxxxxxxxx）をクリック

#### 13-2: インバウンドルールの追加

**EC2 コンソールのセキュリティグループ画面で:**

1. 「インバウンドルール」タブを選択
2. 「インバウンドルールを編集」をクリック
3. 「ルールを追加」をクリック

#### 13-3: PostgreSQL 接続ルールの設定

```
タイプ: PostgreSQL
プロトコル: TCP
ポート範囲: 5432
ソース: 0.0.0.0/0
説明: PostgreSQL access for development
```

#### 13-4: Babelfish 接続ルール（オプション）

```
タイプ: カスタム TCP
プロトコル: TCP
ポート範囲: 1433
ソース: 0.0.0.0/0
説明: Babelfish TDS access
```

#### 13-5: CloudShell 専用ルール（推奨）

より安全な設定として、CloudShell の IP のみ許可する場合：

```bash
# CloudShell で現在の IP を確認
curl -s https://checkip.amazonaws.com
```

```
タイプ: PostgreSQL
プロトコル: TCP
ポート範囲: 5432
ソース: [CloudShellのIP]/32
説明: CloudShell PostgreSQL access
```

#### 13-6: ルール保存

1. 「ルールを保存」をクリック
2. 設定完了の確認

**セキュリティ注意事項**:

- 本番環境では `0.0.0.0/0` は使用せず、特定の IP 範囲に制限
- 開発環境でも定期的にルールを見直し

### Step 14: 接続テスト

#### 14-1: CloudShell からの接続テスト

```bash
# 環境変数設定
export RDS_WRITER_ENDPOINT="whisperplanet-international-data-aurora-dev.cluster-xxxxx.us-west-2.rds.amazonaws.com"
export RDS_DATABASE="whisperplanet-international-data-aurora-dev"
export RDS_USERNAME="postgres"

# 接続テスト（ポート疎通確認）
nc -zv $RDS_WRITER_ENDPOINT 5432

# psql 接続テスト
psql -h $RDS_WRITER_ENDPOINT -U $RDS_USERNAME -d $RDS_DATABASE
```

#### 14-2: 接続成功の確認

```sql
-- 接続情報確認
\conninfo

-- バージョン確認
SELECT version();

-- 終了
\q
```

### Step 15: 接続情報の取得

Aurora クラスターの詳細画面で以下の情報を記録：

```
ライターエンドポイント: whisperplanet-international-data-aurora-dev.cluster-xxxxx.us-west-2.rds.amazonaws.com
リーダーエンドポイント: whisperplanet-international-data-aurora-dev.cluster-ro-xxxxx.us-west-2.rds.amazonaws.com
ポート: 5432, 1433(babelfish)
データベース名: whisperplanet-international-data-aurora-dev
マスターユーザー名: postgres

```

**エンドポイント説明**:

- **ライターエンドポイント**: 書き込み用（データ収集 Lambda 用）
- **リーダーエンドポイント**: 読み取り用（Web UI 用）

## 設定パラメータ一覧

| カテゴリ           | パラメータ                           | 設定値                                       | 説明                          |
| ------------------ | ------------------------------------ | -------------------------------------------- | ----------------------------- |
| **作成方法**       | 作成方法                             | 標準作成                                     | データベース作成方法          |
| **エンジン**       | エンジンタイプ                       | Amazon Aurora                                | データベースエンジン          |
|                    | エディション                         | Amazon Aurora PostgreSQL-Compatible Edition  | PostgreSQL 互換エディション   |
|                    | バージョン                           | Aurora PostgreSQL 15.4                       | データベースバージョン        |
| **テンプレート**   | テンプレート                         | 開発/テスト                                  | コスト最適化設定              |
| **設定**           | DB クラスター識別子                  | whisperplanet-international-data-aurora-dev  | 一意の識別子                  |
|                    | マスターユーザー名                   | postgres                                     | 管理者ユーザー                |
|                    | 認証情報管理                         | Managed in AWS Secrets Manager               | パスワード管理方法            |
|                    | 暗号化キー                           | aws/secretsmanager(default)                  | Secrets Manager 暗号化キー    |
|                    | クラスタストレージ設定               | Aurora Standard                              | ストレージ設定                |
| **インスタンス**   | DB インスタンスクラス                | db.t4g.medium                                | 2 vCPU, 4 GiB RAM (ARM64)     |
| **可用性**         | マルチ AZ 展開                       | Aurora レプリカは作成しない                  | コスト最適化                  |
| **接続**           | コンピューティングリソース           | EC2 コンピューティングリソースに接続しない   | EC2 との接続設定              |
| ネットワークタイプ | IPv4                                 | ネットワークプロトコル                       |
|                    | VPC                                  | デフォルト VPC                               | 仮想プライベートクラウド      |
|                    | DB サブネットグループ                | デフォルト                                   | サブネット設定                |
|                    | パブリックアクセス                   | いいえ                                       | 外部アクセス制限              |
|                    | VPC セキュリティグループ             | default                                      | セキュリティグループ          |
|                    | アベイラビリティーゾーン             | 指定なし                                     | AZ 自動選択                   |
|                    | 認証局                               | rds-ca-rsa2048-g1(default)                   | SSL 証明書認証局              |
|                    | データベースポート                   | 5432                                         | PostgreSQL 標準ポート         |
|                    | リードレプリカ書き込みフォワード     | 無効                                         | 書き込みフォワード設定        |
|                    | Babelfish                            | 有効                                         | SQL Server 互換機能           |
| **認証**           | データベース認証                     | IAM DB 認証                                  | IAM 認証有効化                |
| **モニタリング**   | Database Insights                    | 標準                                         | データベース洞察              |
|                    | Performance insights                 | 有効                                         | パフォーマンス監視            |
|                    | 保有期間                             | 7 日                                         | Performance Insights 保持期間 |
|                    | AWS KMS キー                         | (default)aws/rds                             | Performance Insights 暗号化   |
|                    | 拡張モニタリング                     | 有効                                         | OS レベル監視                 |
|                    | OS メトリクス粒度                    | 60 秒                                        | メトリクス収集間隔            |
|                    | モニタリングロール                   | default                                      | 拡張モニタリング用ロール      |
|                    | ログエクスポート                     | iam-db-auth-error, instance, PostgreSQL log  | CloudWatch ログ出力           |
|                    | IAM ロール                           | RDS service-linked role                      | ログエクスポート用ロール      |
|                    | DevOps Guru                          | 無効                                         | DevOps Guru 連携              |
| **追加設定**       | DB クラスターパラメータグループ      | whisperplanet-international-data-param-group | 新規パラメータグループ        |
| **Babelfish**      | DB 移行モード                        | Single DB                                    | Babelfish 移行モード          |
|                    | デフォルト照合ロケール               | en-US                                        | 照合ロケール                  |
|                    | 照合名                               | sql_latin1_general_cp1_ci_as                 | 照合順序                      |
|                    | TDS ポート                           | 1433                                         | SQL Server 互換ポート         |
|                    | DB パラメータグループ                | default.aurora-postgresql15                  | Babelfish パラメータグループ  |
|                    | フェールオーバ優先                   | 指定なし                                     | フェールオーバー優先度        |
| **バックアップ**   | バックアップ保持期間                 | 7 日                                         | バックアップ保持期間          |
|                    | Copy tags to snapshots               | 有効                                         | スナップショットタグコピー    |
| **暗号化**         | 保存時の暗号化                       | 有効                                         | データ暗号化                  |
|                    | AWS KMS キー                         | (デフォルト) aws/rds                         | 暗号化キー                    |
| **メンテナンス**   | 自動マイナーバージョンアップグレード | 有効                                         | 自動アップグレード            |
|                    | メンテナンスウィンドウ               | 指定なし (AWS が選択)                        | メンテナンス時間              |
|                    | 削除保護                             | 無効                                         | 削除保護設定                  |

## トラブルシューティング

### 接続できない場合

1. **セキュリティグループ確認**

   - インバウンドルール設定確認
   - ポート 5432 が開放されているか

2. **ネットワーク確認**

   - パブリックアクセスが有効か
   - VPC 設定が正しいか

3. **認証情報確認**
   - ユーザー名・パスワードが正しいか
   - データベース名が正しいか

### パフォーマンス問題

1. **インスタンスクラス確認**

   - CPU・メモリ使用率確認
   - 自動スケーリング設定確認
   - 必要に応じて最大容量調整

2. **Aurora 固有の確認**

   - リーダーエンドポイントの負荷分散確認
   - Aurora レプリカの自動追加確認
   - ストレージは自動最適化（手動調整不要）

3. **接続プール最適化**
   - Lambda 関数での接続プール使用
   - pgBouncer 等の接続プール検討

## 次のステップ

1. データベーススキーマの作成 (02-database-schema-setup.md)
2. 初期データの投入
3. アプリケーションからの接続テスト

## Aurora PostgreSQL 特有の利点

### 高可用性

- **自動フェイルオーバー**: 30 秒以内で自動切り替え
- **マルチ AZ**: 3 つの AZ に 6 つのコピーを自動作成
- **自己修復**: 破損したデータブロックを自動修復

### パフォーマンス

- **3 倍高速**: 標準 PostgreSQL の 3 倍のパフォーマンス
- **読み取りレプリカ**: 最大 15 個まで作成可能
- **自動スケーリング**: 負荷に応じて自動でレプリカ追加

### 運用効率

- **継続的バックアップ**: 35 日間のポイントインタイム復旧
- **高速クローン**: 数分でクラスター全体をクローン
- **自動パッチ適用**: ゼロダウンタイムでのパッチ適用

## 注意事項

- **コスト**: RDS より高コストだが、高機能・高性能
- **最小構成**: db.t4g.medium が最小推奨インスタンス
- **パスワード管理**: 安全に管理し、定期的に変更する
- **モニタリング**: Aurora 固有のメトリクスを監視
- **停止制限**: Aurora クラスターは 7 日間のみ停止可能（自動再開）
