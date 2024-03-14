import requests
import json
from get_ids_token import get_token
import sys
import logging

session = requests.session()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("开始打印日志")


def get_bearer_token(username, password):
    """
    获取 CAS 登录的 Bearer Token
    :return: (姓名, Token)
    """
    try:

        # 获取 IDS Token
        ids_token = get_token(username, password)

        # 发起 CAS 登录请求
        headers_get = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/117.0.5938.63 Safari/537.36"
        }
        session.get(url=ids_token, headers=headers_get, allow_redirects=False)
        res = session.get(url="http://libyy.qfnu.edu.cn/api/cas/cas", headers=headers_get, allow_redirects=False)
        cas_token = res.headers["Location"][-32:]

        # 发送 CAS 用户信息请求
        data = {
            "cas": cas_token
        }
        headers_post = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/117.0.5938.63 Safari/537.36",
            "Content-Type": "application/json"
        }
        res = session.post(url="http://libyy.qfnu.edu.cn/api/cas/user", headers=headers_post, data=json.dumps(data))
        parsed_res = json.loads(res.text)

        # 解析响应并返回姓名和 Token
        return parsed_res["member"]["name"], parsed_res["member"]["token"]
    except Exception as e:
        logging.info(f"获取 token 异常，账号密码错误")
        sys.exit()


if __name__ == "__main__":
    # 测试获取 Bearer Token
    name, token = get_bearer_token('', '')
    if name and token:
        print("姓名:", name)
        print("Token:", token)
    else:
        print("获取 Bearer Token 失败")
