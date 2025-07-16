import numpy as np
from typing import List, Union
from datetime import datetime

class GM11Model:
    """
    GM(1,1) 灰色预测模型
    """
    def __init__(self):
        self.a = None  # 发展系数
        self.b = None  # 灰色作用量
        self.original_data = None  # 原始数据

    def fit(self, data: List[Union[int, float]]) -> None:
        """
        训练模型
        :param data: 历史销量数据列表，长度需 >= 4
        """
        if len(data) < 4:
            raise ValueError("GM(1,1) 需要至少4个数据点")

        self.original_data = np.array(data, dtype=float)
        
        # 1. 累加生成序列 (AGO)
        ago = np.cumsum(self.original_data).astype(float)
        
        # 2. 计算紧邻均值生成序列 (Z)
        z = (ago[:-1] + ago[1:]) / 2.0
        
        # 3. 最小二乘法求解参数 a, b
        B = np.vstack((-z, np.ones_like(z))).T
        Y = self.original_data[1:].reshape(-1, 1)
        [[self.a], [self.b]] = np.linalg.lstsq(B, Y, rcond=None)[0]

    def predict(self, steps: int = 1) -> List[float]:
        """
        预测未来 steps 个时间点的值
        :param steps: 预测步长
        :return: 预测值列表
        """
        if self.a is None:
            raise RuntimeError("请先调用 fit() 方法训练模型")

        # 灰色预测方程的解
        # pred_ago = (self.original_data[0] - self.b / self.a) * np.exp(
        #     -self.a * np.arange(1, len(self.original_data) + steps)
        # ) + self.b / self.a
        n = len(self.original_data)
        pred_ago = np.zeros(n + steps)
        pred_ago[0] = self.original_data[0]

        for k in range(1, n + steps):
            pred_ago[k] = (self.original_data[0] - self.b / self.a) * np.exp(-self.a * k) + self.b / self.a

        # 累减还原 (IAGO)
        pred = np.diff(pred_ago, prepend=0)
        # return pred[-steps:].tolist()
        return pred[n:].tolist()

def predict_future_sales(
    historical_sales: List[Union[int, float]],
    historical_months: List[str],
    target_month: str,
) -> float:
    """
    预测未来某个月的销量
    :param historical_sales: 历史销量列表
    :param historical_months: 对应的历史月份列表 (格式: "YYYY-MM")
    :param target_month: 目标月份 (格式: "YYYY-MM")
    :return: 预测销量
    """
    # 检查输入数据
    if len(historical_sales) != len(historical_months):
        raise ValueError("历史销量和月份数量不一致")
    if len(historical_sales) < 4:
        raise ValueError("至少需要4个月的历史数据")

    # 转换为月份差 (假设历史数据是连续的)
    months = [datetime.strptime(m, "%Y-%m") for m in historical_months]
    target = datetime.strptime(target_month, "%Y-%m")
    steps = (target.year - months[-1].year) * 12 + (target.month - months[-1].month)
    if steps <= 0:
        raise ValueError("目标月份必须晚于历史数据最后一个月")

    # 训练模型并预测
    model = GM11Model()
    model.fit(historical_sales)
    return model.predict(steps=steps)[-1]  # 返回最后一步的预测值

# 示例使用
if __name__ == "__main__":
    # 历史数据 (假设输入是连续的月份)
    historical_sales = [100, 100, 100, 100]
    historical_months = ["2025-03", "2025-04", "2025-05", "2025-06", ]
    target_month = "2025-07"

    try:
        pred = predict_future_sales(historical_sales, historical_months, target_month)
        print(f"预测 {target_month} 的销量为: {pred:.2f}")
    except Exception as e:
        print(f"错误: {e}")