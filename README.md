# tvshoki

TV向けメディアの実装リポジトリ。

事業・戦略・タスクの正本は Media_OS にある。
https://github.com/shinojima-rgb/Media_OS

このリポジトリは実装だけを持つ。Brain やタスク設計をここに複製しない。

## 位置づけ

Media_OS/brain/ が事業・戦略・KPI の正本。
Media_OS/tasks/ が仕事の起票と進行。
tvshoki（このリポジトリ）が TV向けメディアの実装。

## 進め方

Media_OS の tasks/inbox に起票された仕事を Cursor Cloud Agent が受け取り、
このリポジトリで branch を切って PR を出す。PR は GrokBot CEO がレビューする。

main へ直接 push しない。変更は PR 経由。

## ステータス

初期化のみ。実装はこれから。

## Media_OS / Cursor Cloud Agent

このリポジトリは Media_OS によって企画・タスク管理され、Cursor Cloud Agent によって実装される。
