import random
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


def generate_random_string(length):
    """
    生成指定长度的随机字符串

    Parameters:
        length (int): 随机字符串的长度

    Returns:
        str: 生成的随机字符串
    """
    aes_chars = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
    return ''.join(random.choice(aes_chars) for _ in range(length))


def encrypt_data(data, key, iv):
    """
    使用 AES 加密数据

    Parameters:
        data (str): 要加密的数据
        key (str): 加密密钥
        iv (str): 初始向量

    Returns:
        str: 加密后的 Base64 编码字符串
    """
    data = data.strip().encode('utf-8')
    key_encoded = key.encode('utf-8')
    iv_encoded = iv.encode('utf-8')

    backend = default_backend()
    cipher = Cipher(algorithms.AES(key_encoded), modes.CBC(iv_encoded), backend=backend)

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()

    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')

    return encrypted_base64


def generate_encrypted_password(passwd, salt):
    """
    生成加密密码

    Parameters:
        passwd (str): 原始密码
        salt (str): 盐值

    Returns:
        str: 加密后的密码
    """
    key = generate_random_string(64)
    iv = generate_random_string(16)
    return encrypt_data(key + passwd, salt, iv)


if __name__ == "__main__":
    # 生成加密密码并打印
    print(generate_encrypted_password('', ''))
