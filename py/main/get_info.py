import base64
import logging
import sys
import time
from datetime import datetime
from datetime import timedelta

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("开始打印日志")

# 创建教室名称到 ID 的映射字典
classroom_id_mapping = {
    "西校区图书馆-三层自习室": 38,
    "西校区图书馆-四层自习室": 39,
    "西校区图书馆-五层自习室": 40,
    "西校区东辅楼-二层自习室": 41,
    "西校区东辅楼-三层自习室": 42,
    "东校区图书馆-三层电子阅览室": 21,
    "东校区图书馆-三层自习室01": 22,
    "东校区图书馆-三层自习室02": 23,
    "东校区图书馆-四层中文现刊室": 24,
    "综合楼-801自习室": 16,
    "综合楼-803自习室": 17,
    "综合楼-804自习室": 18,
    "综合楼-805自习室": 19,
    "综合楼-806自习室": 20,
    "行政楼-四层东区自习室": 13,
    "行政楼-四层中区自习室": 14,
    "行政楼-四层西区自习室": 15,
    "电视台楼-二层自习室": 12
}

# 常量定义
URL_CLASSROOM_DETAIL_INFO = "http://libyy.qfnu.edu.cn/api/Seat/date"
URL_CLASSROOM_SEAT = "http://libyy.qfnu.edu.cn/api/Seat/seat"
URL_CHECK_STATUS = "http://libyy.qfnu.edu.cn/api/Member/seat"

MAX_RETRIES = 100  # 最大重试次数
RETRY_DELAY = 3  # 重试间隔时间(秒)


# 获取预约的日期
def get_date(date):
    try:
        # 判断预约的时间
        if date == "today":
            nowday = datetime.now().date()
        elif date == "tomorrow":
            nowday = datetime.now().date() + timedelta(days=1)
        else:
            logger.error(f"未知的参数: {date}")
            sys.exit()
        # 结果判断
        if nowday:
            # logger.info(f"获取的日期: {nowday}")
            return nowday.strftime("%Y-%m-%d")  # 将日期对象转换为字符串
        else:
            logger.error("日期获取失败")
            sys.exit()

    except Exception as e:
        logger.error(f"获取日期异常: {str(e)}")
        sys.exit()


def send_post_request_and_save_response(url, data, headers):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.post(url, json=data, headers=headers, timeout=120)
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


# 获取教室 id
def get_build_id(classname):
    logger.info(f"教室名称: {classname}")
    # 使用列表的第一个元素作为键来获取相应的值
    build_id = classroom_id_mapping.get(classname)
    # logger.info(build_id)
    return build_id



def get_segment(build_id, nowday):
    try:
        post_data = {
            "build_id": build_id
        }

        request_headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "application/json, text/plain, */*",
            "lang": "zh",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Origin": "http://libyy.qfnu.edu.cn",
            "Referer": "http://libyy.qfnu.edu.cn/h5/index.html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,pl;q=0.5"
        }

        res = send_post_request_and_save_response(URL_CLASSROOM_DETAIL_INFO, post_data, request_headers)
        segment = None
        # logger.info(res)
        # 提取"今天"或者"明天"的教室的 segment
        for item in res['data']:
            if item['day'] == nowday:
                segment = item['times'][0]['id']
                # logger.info(segment)
                break

        return segment
    except Exception as e:
        logger.error(f"获取segment时出错: {str(e)}")
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


def get_member_seat(auth):
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
        return res
        # logger.info(res)

    except KeyError:
        logger.error("数据获取失败, Token 失效，重新获取")
        return None


def get_seat_info(build_id, segment, nowday):
    try:
        interrupted = False
        while not interrupted:
            try:
                post_data = {
                    "area": build_id,
                    "segment": segment,
                    "day": nowday,
                    "startTime": "08:00",
                    "endTime": "22:00",
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
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,pl;q=0.5"
                }

                res = send_post_request_and_save_response(URL_CLASSROOM_SEAT, post_data, request_headers)
                # logger.info(res)
                free_seats = []
                for seat in res['data']:
                    if seat['status_name'] == '空闲':
                        free_seats.append({'id': seat['id'], 'no': seat['no']})

                # logger.info(free_seats)
                time.sleep(1)
                return free_seats

            except requests.exceptions.Timeout:
                logger.warning("请求超时，正在重试...")

            except Exception as e:
                logger.error(f"获取座位信息异常: {str(e)}")
                sys.exit()

            time.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"主动停止程序")
    except Exception as e:
        logger.error(f"循环异常: {str(e)}")
        sys.exit()


if __name__ == "__main__":
    logger.info("")
