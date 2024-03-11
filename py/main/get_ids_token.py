from bs4 import BeautifulSoup
import requests
import time
from ids_utils.passwd_encrypt import generate_encrypted_password
# from ids_utils.captcha_ocr import get_ocr_res
import logging
session = requests.session()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("开始打印日志")


def get_salt_and_execution():
    """
    获取盐值和执行数据

    Returns:
        tuple: (盐值, 执行数据)
    """
    uri = "http://ids.qfnu.edu.cn/authserver/login?service=http%3A%2F%2Flibyy.qfnu.edu.cn%2Fapi%2Fcas%2Fcas"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/117.0.5938.63 Safari/537.36",
        "Referer": "http://libyy.qfnu.edu.cn/"
    }
    response_data = session.get(url=uri, headers=headers).text
    soup_decoded_data = BeautifulSoup(response_data, "html.parser")
    execution_data = soup_decoded_data.find(id='execution').get('value')
    salt_data = soup_decoded_data.find(id='pwdEncryptSalt').get('value')
    return salt_data, execution_data


def captcha_check(username):
    """
    检查是否需要验证码

    Args:
        username (str): 用户名

    Returns:
        bool: 是否需要验证码
    """
    uri = "http://ids.qfnu.edu.cn/authserver/checkNeedCaptcha.htl"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/117.0.5938.63 Safari/537.36"
    }
    data = {
        "username": username,
        "_": int(round(time.time() * 1000))
    }
    res = session.get(url=uri, params=data, headers=headers)
    return "true" in res.text


def get_captcha():
    """
    获取验证码

    Returns:
        bytes: 验证码图片的字节内容
    """
    uri = "http://ids.qfnu.edu.cn/authserver/getCaptcha.htl?" + str(int(round(time.time() * 1000)))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
                Chrome/117.0.5938.63 Safari/537.36"
    }
    res = session.get(url=uri, headers=headers)
    return res.content


def get_token(username, password):
    """
    获取用户 Token

    Args:
        username (str): 用户名
        password (str): 密码

    Returns:
        str: 用户 Token
    """
    cap_res = ""
    salt, execution_data = get_salt_and_execution()
    # logging.info("[+]---正在检查是否需要验证码")
    # if captcha_check(username):
    #     logging.info("[-]------需要验证码，正在尝试获取验证码")
    #     try:
    #         cap_pic = get_captcha()
    #         cap_res = get_ocr_res(cap_pic).lower()
    #     except Exception:
    #         logger.error("[X]------获取或识别验证码失败")
    # else:
    #     logger.info("[-]------无需验证码，尝试获取Token")

    enc_passwd = generate_encrypted_password(password, salt)
    uri = "http://ids.qfnu.edu.cn/authserver/login?service=http%3A%2F%2Flibyy.qfnu.edu.cn%2Fapi%2Fcas%2Fcas"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/117.0.5938.63 Safari/537.36",
        "Referer": "http://ids.qfnu.edu.cn/authserver/login?service=http%3A%2F%2Flibyy.qfnu.edu.cn%2Fapi%2Fcas%2Fcas",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "username": username,
        "password": enc_passwd,
        "captcha": cap_res,
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "lt": "",
        "execution": execution_data
    }

    res = session.post(url=uri, headers=headers, data=data, allow_redirects=False)
    return res.headers["Location"]


if __name__ == '__main__':
    get_token('', '')
