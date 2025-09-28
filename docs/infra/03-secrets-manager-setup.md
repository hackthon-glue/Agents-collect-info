# 03. AWS Secrets Manager 設定手順書

## 概要

国際データ収集システムで使用する API 認証情報を AWS Secrets Manager に安全に保存します。
NewsAPI と OpenWeatherMap API の認証情報を設定します。

## 前提条件

- AWS Management Console へのアクセス権限
- Secrets Manager の作成・管理権限
- NewsAPI と OpenWeatherMap の API キー取得済み

## API キーの取得

### NewsAPI キーの取得

1. **NewsAPI サイトにアクセス**

   - URL: https://newsapi.org/
   - 「Get API Key」をクリック

2. **アカウント作成**

   ```
   Email: [あなたのメールアドレス]
   Password: [安全なパスワード]
   ```

3. **API キー確認**

   - ダッシュボードで API キーを確認
   - 例: `1234567890abcdef1234567890abcdef`

4. **利用制限確認**
   ```
   Free Plan:
   - 1,000 requests/day
   - Development use only
   ```

### OpenWeatherMap キーの取得

1. **OpenWeatherMap サイトにアクセス**

   - URL: https://openweathermap.org/api
   - 「Sign Up」でアカウント作成

2. **アカウント作成**

   ```
   Username: [ユーザー名]
   Email: [メールアドレス]
   Password: [安全なパスワード]
   ```

3. **API キー確認**

   - My API keys ページで API キーを確認
   - 例: `abcdef1234567890abcdef1234567890`

4. **利用制限確認**
   ```
   Free Plan:
   - 1,000 calls/day
   - 60 calls/minute
   ```

## Secrets Manager 設定

### Step 1: AWS Management Console へのアクセス

1. AWS Management Console にログイン
2. リージョンを **オレゴン(us-west-2)** に設定
3. サービス検索で「Secrets Manager」を検索してクリック

### Step 2: 認証情報の設定

#### シークレット作成開始

1. Secrets Manager ダッシュボードで「**新しいシークレットを保存**」をクリック
2. シークレットタイプの選択

#### シークレットタイプ設定

```
シークレットタイプ: その他のシークレットタイプ
```

#### データソース別シークレット作成

**NewsAPI 用シークレット**:

```
シークレット名: whisperplanet/credentials/news
キー/値:
  api_key: [NewsAPIキー]
説明: Authentication credentials for international　news data collection
```

**OpenWeatherMap 用シークレット**:

```
シークレット名: whisperplanet/credentials/weather
キー/値:
  api_key: [OpenWeatherMapキー]
説明: Authentication credentials for international　weather data collection
```

#### 暗号化設定

```
暗号化キー: aws/secretsmanager (デフォルト)
```

#### リソースアクセス許可

```
リソースアクセス許可: 設定しない (デフォルト)
```

### シークレット複製

```
AWS Reagion: 設定しない（デフォルト）
```

#### 自動ローテーション

```
自動ローテーション: 無効
```

**設定理由**: API キーは外部サービスのため手動で管理

#### 確認と作成

1. 設定内容を確認
2. 「**シークレットを保存**」をクリック
3. 作成完了を確認

### Step 2: 作成確認

#### シークレット一覧確認

Secrets Manager ダッシュボードで以下のシークレットが作成されていることを確認：

```
1. whisperplanet/credentials/news
   - 説明: ...
   - 最終更新: [作成日時]
   - 自動ローテーション: 無効

2. whisperplanet/credentials/weather
   - 説明: ...
   - 最終更新: [作成日時]
   - 自動ローテーション: 無効
```

#### シークレット詳細確認

各シークレットをクリックして詳細を確認：

```
ARN: arn:aws:secretsmanager:us-west-2:ACCOUNT-ID:secret:whisperplanet/credentials/news-XXXXXX
リージョン: us-west-2
暗号化: aws/secretsmanager
```

## アクセス権限設定

### Step 3: IAM ポリシー作成

Lambda 関数がシークレットにアクセスできるよう、IAM ポリシー作成：

#### 必要な権限

Ï

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:*:secret:whisperplanet/credentials/*"
      ]
    }
  ]
}
```

## 動作確認

### Step 4: AWS CLI での確認

CloudShell 上で実行する

#### AWS CLI 設定確認

```bash
# AWS CLI設定確認
aws configure list

# リージョン確認
aws configure get region
```

#### シークレット一覧取得

```bash
# シークレット一覧確認
aws secretsmanager list-secrets --region us-west-2

# 特定シークレットの確認
aws secretsmanager describe-secret \
    --secret-id whisperplanet/credentials/news \
    --region us-west-2
```

#### シークレット値取得テスト

```bash
# 認証情報取得
aws secretsmanager get-secret-value \
    --secret-id whisperplanet/credentials/news \
    --region us-west-2
```

**期待される出力例**:

```json
{
  "ARN": "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:newsapi-credentials-AbCdEf",
  "Name": "newsapi-credentials",
  "VersionId": "12345678-1234-1234-1234-123456789012",
  "SecretString": "{\"api_key\":\"1234567890abcdef1234567890abcdef\"}",
  "VersionStages": ["AWSCURRENT"],
  "CreatedDate": "2024-01-01T12:00:00+00:00"
}
```

## 設定パラメータ一覧

### Secrets Manager 設定

| パラメータ              | 値                                                                   | 説明                             |
| ----------------------- | -------------------------------------------------------------------- | -------------------------------- |
| **NewsAPI 設定**        |                                                                      |                                  |
| シークレット名          | `whisperplanet/credentials/news`                                     | NewsAPI 認証情報                 |
| シークレットタイプ      | その他のシークレットタイプ                                           | カスタム JSON                    |
| 暗号化キー              | `aws/secretsmanager`                                                 | デフォルト暗号化                 |
| 自動ローテーション      | 無効                                                                 | 手動管理                         |
| 説明                    | Authentication credentials for international news data collection    | 国際ニュースデータ収集用認証情報 |
| **OpenWeatherMap 設定** |                                                                      |                                  |
| シークレット名          | `whisperplanet/credentials/weather`                                  | 天気 API 認証情報                |
| シークレットタイプ      | その他のシークレットタイプ                                           | カスタム JSON                    |
| 暗号化キー              | `aws/secretsmanager`                                                 | デフォルト暗号化                 |
| 自動ローテーション      | 無効                                                                 | 手動管理                         |
| 説明                    | Authentication credentials for international weather data collection | 国際天気データ収集用認証情報     |

### JSON 構造

| シークレット                      | JSON 構造              | 例                                   |
| --------------------------------- | ---------------------- | ------------------------------------ |
| whisperplanet/credentials/news    | `{"api_key": "VALUE"}` | `{"api_key": "1234567890abcdef..."}` |
| whisperplanet/credentials/weather | `{"api_key": "VALUE"}` | `{"api_key": "abcdef1234567890..."}` |

### ARN 形式

```
NewsAPI: arn:aws:secretsmanager:us-west-2:ACCOUNT-ID:secret:whisperplanet/credentials/news-XXXXXX
OpenWeatherMap: arn:aws:secretsmanager:us-west-2:ACCOUNT-ID:secret:whisperplanet/credentials/weather-XXXXXX
```

## セキュリティ考慮事項

### 監査とログ

1. **CloudTrail ログ**

   - シークレットアクセスの記録
   - 不正アクセスの検出

2. **CloudWatch メトリクス**

   - シークレット取得回数の監視
   - 異常なアクセスパターンの検出

## トラブルシューティング

### シークレット作成エラー

1. **権限不足**

   ```
   エラー: User is not authorized to perform: secretsmanager:CreateSecret
   対処: IAMユーザーにSecretsManager権限を付与
   ```

2. **重複名エラー**
   ```
   エラー: A resource with the ID "newsapi-credentials" already exists
   対処: 異なるシークレット名を使用するか、既存を削除
   ```

### シークレット取得エラー

1. **シークレットが見つからない**

   ```python
   # シークレット存在確認
   try:
       response = secrets_client.describe_secret(SecretId='newsapi-credentials')
       print("Secret exists")
   except secrets_client.exceptions.ResourceNotFoundException:
       print("Secret not found")
   ```

2. **権限エラー**
   ```python
   # 権限確認
   try:
       response = secrets_client.get_secret_value(SecretId='newsapi-credentials')
   except secrets_client.exceptions.AccessDeniedException:
       print("Access denied - check IAM permissions")
   ```

### API 接続エラー

1. **API キー無効**

   ```
   NewsAPI: HTTP 401 - Invalid API key
   OpenWeatherMap: HTTP 401 - Invalid API key
   対処: APIキーの再確認・再取得
   ```

2. **レート制限**
   ```
   NewsAPI: HTTP 429 - Too many requests
   OpenWeatherMap: HTTP 429 - Too many requests
   対処: リクエスト頻度の調整
   ```

## 次のステップ

1. Lambda 実行用 IAM ロール作成 (04-iam-role-setup.md)
2. Python 開発環境構築
3. データ収集機能の実装

## 注意事項

- API キーは定期的に更新する
- 本番環境では自動ローテーションの検討
- シークレットアクセスログの定期確認
- 不要なシークレットは削除してコスト削減
- API の利用制限を常に確認する
