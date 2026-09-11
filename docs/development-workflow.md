# 開発の進め方

Issueに目的と受入条件、PRに変更と検証、docsに確定設計を記録します。作業branch → PR → CI確認 → mergeで進めます。default branchへの直接push・force push・保護の迂回は禁止です。

検証コマンドはAGENTS.mdを参照。ハードウェア操作は明示された対象のみ。未検証の実機動作を成功扱いしません。

## 導入状況（2026-09-11）

- 公開repo: https://github.com/SHOHE001/mpu-monitor
- GitHubで初期READMEを作成、default branchはmain。
- AGENTS.md / CLAUDE.md、Issue Forms、PRテンプレート、blockedラベル: 導入済み。
- CI: `.github/workflows/ci.yml`。Windows Python checksとFirmware build。初回実行待ち。
- main保護: 初回は未設定（API 404）、Rulesetなし。初回CI成功後に必須チェック・PR必須・force push禁止・削除禁止を設定予定。
- 既存Development HQへIssue #1を登録済み、作業状態とAgentを同期。Projectは既存の公開範囲を維持。
- 認証情報・PCの個人パス・機器のMACアドレス・生ログは公開しません。
