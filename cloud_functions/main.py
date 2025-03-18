import os
import requests

import functions_framework
from google.auth import default
from google.auth.transport.requests import Request
from flask import jsonify

# HTTP トリガーの Cloud Function
@functions_framework.http
def trigger_cloud_run_job(request):
    # リクエストの JSON データを取得
    ret = request.get_json(silent=True)
    if ret.get("type") == "url_verification":
        return jsonify({"challenge": ret["challenge"]})
    # Cloud Run Job の設定
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION")
    job_name = os.getenv("JOB_NAME")

    # Cloud Run Job のエンドポイント
    url = f"https://{region}-run.googleapis.com/v2/projects/{project_id}/locations/{region}/jobs/{job_name}:run"

    # 認証トークンの取得
    credentials, _ = default()
    credentials.refresh(Request())
    auth_token = credentials.token

    # API リクエストのヘッダー
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    # ジョブ実行リクエスト
    response = requests.post(url, headers=headers)

    # 結果を返す
    if response.status_code == 200:
        pass
        ret["result"] = "Job started successfully"
    else:
        ret["result"] = "Job failed to start"
        ret["error"] = response.text
    return jsonify(ret)
