import asyncio
import concurrent.futures
import datetime
import logging
import os
import random
import sys
import time

import requests
import yaml
from telegram import Bot
from get_bearer_token import get_bearer_token
from get_info import get_date, get_seat_info, get_segment, get_build_id, get_auth_token, encrypt

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_GET_SEAT = "http://libyy.qfnu.edu.cn/api/Seat/confirm"
URL_CHECK_STATUS = "http://libyy.qfnu.edu.cn/api/Member/seat"

# 配置文件
CHANNEL_ID = ""
TELEGRAM_BOT_TOKEN = ""
MODE = ""
CLASSROOMS_NAME = ""
SEAT_ID = ""
DATE = ""
USERNAME = ""
PASSWORD = ""
GITHUB = ""
BARK_URL = ""
BARK_EXTRA = ""


# 读取YAML配置文件并设置全局变量
def read_config_from_yaml():
    global CHANNEL_ID, TELEGRAM_BOT_TOKEN,  \
        CLASSROOMS_NAME, MODE, SEAT_ID, DATE, USERNAME, PASSWORD, GITHUB, BARK_EXTRA, BARK_URL
    current_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前文件所在的目录的绝对路径
    config_file_path = os.path.join(current_dir, 'config.yml')  # 将文件名与目录路径拼接起来
    with open(config_file_path, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
        CHANNEL_ID = config.get('CHANNEL_ID', '')
        TELEGRAM_BOT_TOKEN = config.get('TELEGRAM_BOT_TOKEN', '')
        CLASSROOMS_NAME = config.get("CLASSROOMS_NAME", [])
        MODE = config.get("MODE", "")
        SEAT_ID = config.get("SEAT_ID", "")
        DATE = config.get("DATE", "")
        USERNAME = config.get('USERNAME', '')
        PASSWORD = config.get('PASSWORD', '')
        GITHUB = config.get("GITHUB", "")
        BARK_URL = config.get("BARK_URL", "")
        BARK_EXTRA = config.get("BARK_EXTRA", "")


# 在代码的顶部定义全局变量
FLAG = False
SEAT_RESULT = {}
MESSAGE = ""
AUTH_TOKEN = ""
NEW_DATE = ""
TOKEN_TIMESTAMP = None
TOKEN_EXPIRY_DELTA = datetime.timedelta(hours=1, minutes=30) 

# 配置常量
EXCLUDE_ID = {'7443', '7448', '7453', '7458', '7463', '7468', '7473', '7478', '7483', '7488', '7493', '7498', '7503',
              '7508', '7513', '7518', '7572', '7575', '7578', '7581', '7584', '7587', '7590', '7785', '7788', '7791',
              '7794', '7797', '7800', '7803', '7806', '7291', '7296', '7301', '7306', '7311', '7316', '7321', '7326',
              '7331', '7336', '7341', '7346', '7351', '7356', '7361', '7366', '7369', '7372', '7375', '7378', '7381',
              '7384', '7387', '7390', '7417', '7420', '7423', '7426', '7429', '7432', '7435', '7438', '7115', '7120',
              '7125', '7130', '7135', '7140', '7145', '7150', '7155', '7160', '7165', '7170', '7175', '7180', '7185',
              '7190', '7241', '7244', '7247', '7250', '7253', '7256', '7259', '7262', '7761', '7764', '7767', '7770',
              '7773', '7776', '7779', '7782'}
MAX_RETRIES = 200  # 最大重试次数


# 打印变量
def print_variables():
    variables = {
        "CHANNEL_ID": CHANNEL_ID,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "MODE": MODE,
        "CLASSROOMS_NAME": CLASSROOMS_NAME,
        "SEAT_ID": SEAT_ID,
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD,
        "GITHUB": GITHUB,
        "BARK_URL": BARK_URL,
        "BARK_EXTRA": BARK_EXTRA
    }
    for var_name, var_value in variables.items():
        logger.info(f"{var_name}: {var_value} - {type(var_value)}")


# post 请求
def send_post_request_and_save_response(url, data, headers):
    global MESSAGE
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.post(url, json=data, headers=headers, timeout=25)
            response.raise_for_status()
            response_data = response.json()
            return response_data
        except requests.exceptions.Timeout:
            logger.error("请求超时，正在重试...")
            retries += 1
        except Exception as e:
            logger.error(f"request请求异常: {str(e)}")
            retries += 1
    logger.error("超过最大重试次数,请求失败。")
    MESSAGE += "\n超过最大重试次数,请求失败。"
    send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
    asyncio.run(send_seat_result_to_channel())
    sys.exit()


# get 请求
def send_get_request(url):
    try:
        response = requests.get(url)
        # 检查响应状态码是否为200
        if response.status_code == 200:
            logger.info("成功推送消息到 Bark")
            # 返回响应内容
            return response.text
        else:
            logger.error(f"推送到 Bark 的 GET请求失败，状态码：{response.status_code}")
            return None
    except requests.exceptions.RequestException:
        logger.info("GET请求异常, 你的 BARK 链接不正确")
        return None


async def send_seat_result_to_channel():
    try:
        # 使用 API 令牌初始化您的机器人
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        # logger.info(f"要发送的消息为： {MESSAGE}\n")
        await bot.send_message(chat_id=CHANNEL_ID, text=MESSAGE)
    except Exception as e:
        logger.info(f"发送消息到 Telegram 失败，你应该没有填写 token 和 id")
        return e

def get_auth_token(username, password):
    global TOKEN_TIMESTAMP
    try:
        # 如果未从配置文件中读取到用户名或密码，则抛出异常
        if not username or not password:
            raise ValueError("未找到用户名或密码")

        # 检查 Token 是否过期
        if TOKEN_TIMESTAMP is None or (datetime.datetime.now() - TOKEN_TIMESTAMP) > TOKEN_EXPIRY_DELTA:
            # Token 过期或尚未获取，重新获取
            name, token = get_bearer_token(username, password)
            logger.info(f"成功获取授权码")
            new_token = "bearer" + str(token)
            # 更新 Token 的时间戳
            TOKEN_TIMESTAMP = datetime.datetime.now()
            return new_token
        else:
            logger.info("使用现有授权码")
            return new_token
    except Exception as e:
        logger.error(f"获取授权码时发生异常: {str(e)}")
        sys.exit()


def check_book_status(auth):
    global MESSAGE
    global TOKEN_EXPIRY
    # 检查 Token 是否过期
    if datetime.datetime.now() > TOKEN_EXPIRY:
        # Token 已过期，重新获取
        AUTH_TOKEN = get_auth_token(USERNAME, PASSWORD)
        # 更新 Token 的过期时间
        TOKEN_EXPIRY = datetime.datetime.now() + TOKEN_EXPIRY_DELTA
    try:
        post_data = {
            "page": 1,
            "limit": 3,
            "authorization": auth
        }
        request_headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "application/json, text/plain, */*",
            "lang": "zh",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, "
                          "like Gecko)"
                          "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Origin": "http://libyy.qfnu.edu.cn",
            "Referer": "http://libyy.qfnu.edu.cn/h5/index.html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,pl;q=0.5",
            "Authorization": auth
        }
        res = send_post_request_and_save_response(URL_CHECK_STATUS, post_data, request_headers)
        # logger.info(res)
        for entry in res["data"]["data"]:
            if entry["statusName"] == "预约成功" and DATE == "tomorrow":
                logger.info("存在已经预约的座位")
                MESSAGE += "\n存在已经预约的座位"
                send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
                asyncio.run(send_seat_result_to_channel())
                sys.exit()
            elif entry["statusName"] == "使用中" and DATE == "today":
                logger.info("存在正在使用的座位")
                MESSAGE += "\n存在正在使用的座位"
                send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
                asyncio.run(send_seat_result_to_channel())
                # 发送中断信号停止整个程序
                sys.exit()
    except KeyError:
        logger.error("数据获取失败")
        MESSAGE += "\n数据获取失败"
        send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
        asyncio.run(send_seat_result_to_channel())
        sys.exit()


# 状态检测函数
def check_reservation_status(auth_token):
    global SEAT_RESULT, FLAG, MESSAGE
    check_book_status(auth_token)
    # 状态信息检测
    if 'msg' in SEAT_RESULT:
        status = SEAT_RESULT['msg']
        logger.info(status)
        if status == "当前时段存在预约，不可重复预约!":
            logger.info("重复预约, 请检查选择的时间段或是否已经成功预约")
            MESSAGE += "\n重复预约, 请检查选择的时间段或是否已经成功预约"
            send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
            asyncio.run(send_seat_result_to_channel())
            sys.exit()
        elif status == "预约成功":
            # elif "1" == "1":
            logger.info("成功预约")
            MESSAGE += f"\n预约状态为:{status}"
            send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
            asyncio.run(send_seat_result_to_channel())
            sys.exit()
        elif status == "开放预约时间19:20":
            logger.info("未到预约时间")
            MESSAGE += f"\n预约状态为:{status}"
            send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
            asyncio.run(send_seat_result_to_channel())
            # 理论来说是到不了这一句的
            time.sleep(5)
        elif status == "您尚未登录":
            logger.info("没有登录，请检查是否正确获取了 token")
            MESSAGE += f"\n预约状态为:{status}"
            MESSAGE += "\n没有登录，请检查是否正确获取了 token"
            send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
            asyncio.run(send_seat_result_to_channel())
            sys.exit()
        elif status == "该空间当前状态不可预约":
            logger.info("此位置已被预约")
            if MODE == "2":
                logger.info("此座位已被预约，请在 config 中修改 SEAT_ID 后重新预约")
                MESSAGE += f"\n预约状态为:{status}"
                send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
                asyncio.run(send_seat_result_to_channel())
                sys.exit()
            else:
                logger.info(f"选定座位已被预约，重新选定")
        else:
            logger.error("未知状态，程序退出")
            MESSAGE += "\n未知状态，程序退出"
            send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
            asyncio.run(send_seat_result_to_channel())
            sys.exit()
    else:
        logger.error("没有获取到状态信息，token已过期")
        MESSAGE += "\n没有获取到状态信息，token已过期"
        send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
        asyncio.run(send_seat_result_to_channel())
        sys.exit()


# 预约函数
def post_to_get_seat(select_id, segment, auth):
    # 定义全局变量
    global SEAT_RESULT
    # 原始数据
    origin_data = '{{"seat_id":"{}","segment":"{}"}}'.format(select_id, segment)
    # logger.info(origin_data)

    # 加密数据
    aes_data = encrypt(str(origin_data))
    # aes_data = "test"
    # logger.info(aes_data)

    # 测试解密数据
    # aes = decrypt(aes_data)
    # logger.info(aes)

    # 原始的 post_data
    post_data = {
        "aesjson": aes_data,
    }

    request_headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "lang": "zh",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, "
                      "like Gecko)"
                      "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Origin": "http://libyy.qfnu.edu.cn",
        "Referer": "http://libyy.qfnu.edu.cn/h5/index.html",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,pl;q=0.5",
        "Authorization": auth
    }

    # 发送POST请求并获取响应
    SEAT_RESULT = send_post_request_and_save_response(URL_GET_SEAT, post_data, request_headers)


# 随机获取座位
def random_get_seat(data):
    global MESSAGE
    # 随机选择一个字典
    random_dict = random.choice(data)
    # 获取该字典中 'id' 键对应的值
    select_id = random_dict['id']
    seat_no = random_dict['no']
    logger.info(f"随机选择的座位为: {select_id} 真实位置: {seat_no}")
    MESSAGE = f"随机选择的座位为: {select_id} 真实位置: {seat_no} \n"
    return select_id


# 选座主要逻辑
def select_seat(auth, build_id, segment, nowday):
    # 初始化
    try:
        while not FLAG:
            # 获取座位信息
            data = get_seat_info(build_id, segment, nowday)
            # 优选逻辑
            if MODE == "1":
                new_data = [d for d in data if d['id'] not in EXCLUDE_ID]
                # logger.info(new_data)
                # 检查返回的列表是否为空
                if not new_data:
                    logger.info("无可用座位, 程序将 1s 后再次获取")
                    time.sleep(1)
                    continue
                else:
                    select_id = random_get_seat(new_data)
                    check_reservation_status(auth)
                    post_to_get_seat(select_id, segment, auth)
            # 指定逻辑
            elif MODE == "2":
                logger.info(f"你选定的座位为: {SEAT_ID}")
                post_to_get_seat(SEAT_ID, segment, auth)
                check_reservation_status(auth)
            # 默认逻辑
            elif MODE == "3":
                # 检查返回的列表是否为空
                if not data:
                    logger.info("无可用座位, 程序将 3s 后再次获取")
                    time.sleep(3)
                    continue
                else:
                    select_id = random_get_seat(data)
                    post_to_get_seat(select_id, segment, auth)
                    check_reservation_status(auth)
            else:
                logger.error(f"未知的模式: {MODE}")

    except KeyboardInterrupt:
        logger.info(f"接收到中断信号，程序将退出。")


def process_classroom(classroom_name):
    build_id = get_build_id(classroom_name)
    segment = get_segment(build_id, NEW_DATE)
    select_seat(AUTH_TOKEN, build_id, segment, NEW_DATE)


# 主函数
def get_info_and_select_seat():
    global AUTH_TOKEN, NEW_DATE, MESSAGE
    try:
        if DATE == "tomorrow":
            while True:
                # 获取当前时间
                current_time = datetime.datetime.now()
                # 如果是 Github Action 环境
                if GITHUB:
                    current_time += datetime.timedelta(hours=8)
                # 设置预约时间为19:20
                reservation_time = current_time.replace(hour=19, minute=20, second=0, microsecond=0)
                # 计算距离预约时间的秒数
                time_difference = (reservation_time - current_time).total_seconds()
                # 打印当前时间和距离预约时间的秒数
                logger.info(f"当前时间: {current_time}")
                logger.info(f"距离预约时间还有: {time_difference} 秒")
                # 如果距离时间过长，自动停止程序
                if time_difference > 1000:
                    logger.info("距离预约时间过长，程序将自动停止。")
                    MESSAGE += "\n距离预约时间过长，程序将自动停止"
                    send_get_request(BARK_URL + MESSAGE + BARK_EXTRA)
                    asyncio.run(send_seat_result_to_channel())
                    sys.exit()
                # 如果距离时间在合适的范围内, 将设置等待时间
                elif 1000 >= time_difference > 300:
                    time.sleep(30)
                elif 300 >= time_difference > 60:
                    time.sleep(5)
                else:
                    break

        # 默认逻辑
        logger.info(CLASSROOMS_NAME)
        NEW_DATE = get_date(DATE)
        AUTH_TOKEN = get_auth_token(USERNAME, PASSWORD)
        check_book_status(AUTH_TOKEN)

        # 多线程执行程序
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_classroom, name): name for name in CLASSROOMS_NAME}
            # 等待任一线程完成
            done, not_done = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
            # 取消尚未完成的线程
            for future in not_done:
                future.cancel()

    except KeyboardInterrupt:
        logger.info("主动退出程序，程序将退出。")


if __name__ == "__main__":
    try:
        read_config_from_yaml()
        # print_variables()
        get_info_and_select_seat()

    except KeyboardInterrupt:
        logger.info("主动退出程序，程序将退出。")
