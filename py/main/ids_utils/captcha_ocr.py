import ddddocr

# 初始化 OCR 实例
ocr = ddddocr.DdddOcr()


def get_ocr_res(image_bytes):
    """
    使用 OCR 实例识别给定图像的内容

    Parameters:
        image_bytes (bytes): 图像的字节数据

    Returns:
        str: 图像中识别出的文本结果
    """
    result = ocr.classification(image_bytes)
    return result


if __name__ == "__main__":
    # 外部函数调用
    get_ocr_res('')
