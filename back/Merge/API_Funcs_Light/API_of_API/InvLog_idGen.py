'''
    仓库补货

    传入
    {
        str:product: 商品编号
        str:quantity: 补货数量
        str:warehouse_id: 仓库编号
    }
    返回
    {
        bool:success: 是否登录成功
        array(str, str): 商店编号, 商店名称
    }
'''

from datetime import datetime

def id_format(prefix) -> str:
    current_date = datetime.now().date()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    log_format = f"{prefix}{year % 100:02d}{month:02d}{day:02d}"
    return log_format

def get_id(prefix, cnt) -> str:
    current_date = datetime.now().date()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    id = f"{prefix}{year % 100:02d}{month:02d}{day:02d}{format(cnt, "03d")}"
    return id

if __name__ == '__main__':
    print(id_format("LOG"))
    print(get_id("LOG", 12))