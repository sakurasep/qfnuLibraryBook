import base64
import logging
import multiprocessing
import random
import time
from datetime import datetime
import getpass

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import sys
from get_bearer_token import get_bearer_token
from get_info import get_date, get_seat_info, get_segment, get_build_id

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL_GET_SEAT = "http://libyy.qfnu.edu.cn/api/Seat/confirm"

# 在代码的顶部定义全局变量
global_exclude_ids = set()
seat_result = {}


# 读取授权码
def get_auth_token():
    # token = "test"
    # return token
    try:
        # 从命令行中获取用户名和密码
        username = input("请输入用户名（学号）: \n")
        password = getpass.getpass('请输入密码: \n')
        name, token = get_bearer_token(username, password)
        logger.info(f"你好，{name}同学")
        new_token = "bearer" + str(token)
        # logger.info(new_token)
        return new_token
    except Exception as e:
        logger.error(f"获取授权码时发生异常: {str(e)}")
        sys.exit()


MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 5  # 重试间隔时间(秒)


def send_post_request_and_save_response(url, data, headers):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            response_data = response.json()
            return response_data
        except requests.exceptions.Timeout:
            logger.error("请求超时，正在重试...")
            retries += 1
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"request请求异常: {str(e)}")
            retries += 1
            time.sleep(RETRY_DELAY)
    logger.error("超过最大重试次数,请求失败。")
    sys.exit()


# 根据当前系统时间获取 key
def get_key():
    # 获取当前日期，并转换为字符串
    current_date = datetime.now().strftime("%Y%m%d")

    # 生成回文
    palindrome = current_date[::-1]

    # 使用当前日期和回文作为密钥
    key = current_date + palindrome

    # print("当前日期:", current_date)
    # print("回文:", palindrome)
    # print("密钥:", key)

    return key


# 加密函数
def encrypt(text):
    # 自动获取 key
    key = get_key()
    # 目前获取到的加密密钥
    iv = "ZZWBKJ_ZHIHUAWEI"
    key_bytes = key.encode('utf-8')
    iv_bytes = iv.encode('utf-8')

    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    ciphertext_bytes = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))

    return base64.b64encode(ciphertext_bytes).decode('utf-8')


# 定义解密函数
def decrypt(ciphertext):
    # 自动获取 key
    key = get_key()
    # 目前获取到的加密密钥
    iv = "ZZWBKJ_ZHIHUAWEI"

    # 将密钥和初始化向量转换为 bytes 格式
    key_bytes = key.encode('utf-8')
    iv_bytes = iv.encode('utf-8')

    # 将密文进行 base64 解码
    ciphertext = base64.b64decode(ciphertext)

    # 使用 AES 进行解密
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    decrypted_bytes = cipher.decrypt(ciphertext)

    # 去除解密后的填充
    decrypted_text = unpad(decrypted_bytes, AES.block_size).decode('utf-8')

    return decrypted_text


# 状态检测函数
def check_reservation_status(seat_id, m):
    global seat_result
    # 状态信息检测
    if 'msg' in seat_result:
        status = seat_result['msg']
    else:
        return False

    logger.info(status)

    if status == "当前时段存在预约，不可重复预约!":
        logger.info("重复预约, 请检查选择的时间段或是否已经成功预约")
        return True
    elif status == "预约成功":
        logger.info("成功预约")
        return True
    elif status == "开放预约时间19:20":
        logger.info("未到预约时间,程序将会 10s 查询一次")
        time.sleep(10)
        return False
    elif status == "您尚未登录":
        logger.info("没有登录，请检查是否正确获取了 token")
        return True
    elif status == "该空间当前状态不可预约":
        logger.info("此位置已被预约")
        if m == "2":
            new_seat_id = input("请重新输入想要预约的相同自习室的 id:\n")
            return False, new_seat_id
        else:
            logger.info(f"{seat_id} 已被预约，加入排除名单")
            global_exclude_ids.add(seat_id)
            time.sleep(1)
            # logger.info(global_exclude_ids)
            return False

    else:
        logger.info("未知状态，程序退出")
        return True


# 预约函数
def post_to_get_seat(select_id, segment, auth):
    # 定义全局变量
    global seat_result
    # 原始数据
    origin_data = '{{"seat_id":"{}","segment":"{}"}}'.format(select_id, segment)
    # logger.info(origin_data)

    # 加密数据
    aes_data = encrypt(str(origin_data))
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
    seat_result = send_post_request_and_save_response(URL_GET_SEAT, post_data, request_headers)


# 优选函数
def prefer_get_select_id(build_id):
    try:
        # 根据 build_id 选择相应的优选模式
        if build_id == 38:
            logger.info("你选择的是三层的优选模式")
            valid_ranges = list(range(7112, 7152)) + list(range(7192, 7216)) + list(range(7240, 7263))
        elif build_id == 39:
            logger.info("你选择的是四层的优选模式")
            valid_ranges = list(range(7288, 7328)) + list(range(7368, 7392))
        elif build_id == 40:
            logger.info("你选择的是五层的优选模式")
            valid_ranges = list(range(7440, 7480)) + list(range(7520, 7544)) + list(range(7568, 7591))
        else:
            logger.error("不支持的优选位置")
            sys.exit()

        # 过滤排除的座位 id
        valid_seats = [seat_id for seat_id in valid_ranges if seat_id not in global_exclude_ids]

        # 随机选择一个座位 id
        if valid_seats:
            select_id = random.choice(valid_seats)
            return select_id
        else:
            logger.warning("没有符合条件的座位可供选择")
            return None
    except KeyboardInterrupt:
        logger.info(f"接收到中断信号，程序将退出。")


# 模式1 && 3
def get_and_select_seat_default(auth, build_id, segment, nowday, m):
    # 初始化
    interrupted = False
    try:
        while not interrupted:
            if m == "1":
                # logger.info(build_id)
                select_id = prefer_get_select_id(build_id)
                logger.info(f"优选的座位是:{select_id}")
            else:
                # logger.info(f"获取的 segment: {segment}")
                data = get_seat_info(build_id, segment, nowday)
                # 检查返回的列表是否为空
                if not data:
                    logger.info("无可用座位")
                    continue
                else:
                    # 随机选择一个字典
                    random_dict = random.choice(data)

                    # 获取该字典中 'id' 键对应的值
                    select_id = random_dict['id']
                    seat_no = random_dict['no']

                    logger.info(f"随机选择的座位为: {select_id} 真实位置: {seat_no}")

            if select_id is None:
                logger.info("选定座位为空, 程序继续运行")
                time.sleep(1)
                continue
            else:
                post_to_get_seat(select_id, segment, auth)
                # logger.info(seat_result)
                interrupted = check_reservation_status(select_id, "1")

    except KeyboardInterrupt:
        logger.info(f"接收到中断信号，程序将退出。")


# 模式2
def get_and_select_seat_selected(auth, segment, seat_id):
    # 初始化
    global seat_result
    interrupted = False
    try:
        while not interrupted:
            logger.info(f"你选定的座位为: {seat_id}")
            post_to_get_seat(seat_id, segment, auth)
            # logger.info(seat_result)
            interrupted, seat_id = check_reservation_status(seat_id, "2")

    except KeyboardInterrupt:
        logger.info(f"接收到中断信号，程序将退出。")


# 进程池
def process_classroom(auth, name, process_num, nowday, m):
    try:
        # 获取基本信息
        build_id = get_build_id(name)
        segment = get_segment(build_id, nowday)
        # 进程池
        with multiprocessing.Pool(processes=process_num) as pool:
            params = [(auth, build_id, segment, nowday, m)] * process_num
            pool.starmap(get_and_select_seat_default, params)
        logger.info("进程完成")
    except KeyboardInterrupt:
        logger.info("收到中断信号，程序将退出")


def default_get_seat(m):
    try:
        # 输入基本信息
        classroom_names = input("请输入教室名（多个教室名以空格分隔）:\n").split()
        process_number = int(input("请输入进程数: \n"))
        date = get_date()

        # 获取授权码
        auth_token = get_auth_token()

        processes = []

        for classroom_name in classroom_names:
            p = multiprocessing.Process(target=process_classroom,
                                        args=(auth_token, classroom_name, process_number, date, m))
            processes.append(p)
            p.start()

        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("主动退出程序，程序将退出。")


def selected_get_seat():
    try:
        # 输入基本信息
        classroom_names = input("请输入教室名: \n").split()
        seat_id = input("请输入预选座位的 id（非真实id）:\n")
        date = get_date()

        # 获取授权码
        auth_token = get_auth_token()

        # 获取基本信息
        for classroom_name in classroom_names:
            build_id = get_build_id(classroom_name)
            segment = get_segment(build_id, date)
            get_and_select_seat_selected(auth_token, segment, seat_id)

    except KeyboardInterrupt:
        print("主动退出程序，程序将退出。")


if __name__ == "__main__":
    try:
        # 三种功能
        mode = input("请输入选座模式，1:优选模式 2:指定座位 3:默认随机\n")
        if mode == "3":
            default_get_seat(mode)
        if mode == "2":
            selected_get_seat()
        if mode == "1":
            default_get_seat(mode)
        else:
            sys.exit()

    except KeyboardInterrupt:
        print("主动退出程序，程序将退出。")
