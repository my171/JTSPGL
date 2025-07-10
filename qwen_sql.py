import os
import sys
import time
from openai import OpenAI


def main():
    client = OpenAI(
        api_key="sk-9b72700e16234e9fa4a42bf949fe8327",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    output_file = "database_data.sql"

    # 清空或创建文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-- 数据库填充数据\n\n")

    # 表结构信息
    table_schema = """
        -- 仓库表
        CREATE TABLE warehouse (
            warehouse_id VARCHAR(10) PRIMARY KEY,
            warehouse_name VARCHAR(50) NOT NULL,
            address VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 门店表
        CREATE TABLE store (
            store_id VARCHAR(10) PRIMARY KEY,
            store_name VARCHAR(50) NOT NULL,
            address VARCHAR(100) NOT NULL,
            region VARCHAR(20) NOT NULL,
            opened_date DATE
        );

        -- 商品表
        CREATE TABLE product (
            product_id VARCHAR(20) PRIMARY KEY,
            product_name VARCHAR(50) NOT NULL,
            category VARCHAR(20) NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            cost_price DECIMAL(10,2),
            barcode VARCHAR(20) UNIQUE
        );

        -- 仓库库存表
        CREATE TABLE warehouse_inventory (
            warehouse_id VARCHAR(10),
            product_id VARCHAR(20),
            record_date DATE DEFAULT CURRENT_DATE,
            quantity INT NOT NULL CHECK (quantity >= 0),
            PRIMARY KEY (warehouse_id, product_id, record_date),
            FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );

        -- 门店库存表
        CREATE TABLE store_inventory (
            store_id VARCHAR(10),
            product_id VARCHAR(20),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            stock_quantity INT NOT NULL CHECK (stock_quantity >= 0),
            safety_stock INT,
            PRIMARY KEY (store_id, product_id),
            FOREIGN KEY (store_id) REFERENCES store(store_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );

        -- 销售表
        CREATE TABLE sales (
            sales_id VARCHAR(20) PRIMARY KEY,
            store_id VARCHAR(10) NOT NULL,
            product_id VARCHAR(20) NOT NULL,
            sale_date DATE NOT NULL,
            quantity INT NOT NULL CHECK (quantity > 0),
            unit_price DECIMAL(10,2) NOT NULL,
            total_amount DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
            FOREIGN KEY (store_id) REFERENCES store(store_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );

        -- 补货表
        CREATE TABLE replenishment (
            replenishment_id VARCHAR(20) PRIMARY KEY,
            warehouse_id VARCHAR(10) NOT NULL,
            store_id VARCHAR(10) NOT NULL,
            product_id VARCHAR(20) NOT NULL,
            shipment_date DATE NOT NULL,
            shipped_quantity INT NOT NULL CHECK (shipped_quantity > 0),
            received_quantity INT CHECK (received_quantity >= 0),
            status VARCHAR(15) DEFAULT 'SHIPPED',
            FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
            FOREIGN KEY (store_id) REFERENCES store(store_id),
            FOREIGN KEY (product_id) REFERENCES product(product_id)
        );

        -- 库存流水表
        CREATE TABLE inventory_log (
            log_id VARCHAR(20) PRIMARY KEY,
            product_id VARCHAR(20) NOT NULL,
            location_id VARCHAR(10) NOT NULL,
            change_type VARCHAR(10) NOT NULL CHECK (change_type IN ('IN', 'OUT')),
            change_quantity INT NOT NULL CHECK (change_quantity > 0),
            reference_no VARCHAR(20),
            log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            operator VARCHAR(20),
            FOREIGN KEY (product_id) REFERENCES product(product_id));
        """

    # 强化提示词
    base_prompt = f"""
    请生成标准SQL INSERT VALUES语句，严格遵循：
    ##### 核心要求
    1. 必须使用显式VALUES格式，禁止SELECT/UNION等复杂语法
    2. 时间范围：2024-01-01到2025-06-30均匀分布
    3. 区域覆盖：华北、华东、华南、华中、西南、西北、东北
    4. 商品比例：
        - 电子产品15% (¥500-¥20,000)
        - 食品饮料30% (¥5-¥500)
        - 服装鞋帽25% (¥50-¥3,000)
        - 家居用品20% (¥100-¥8,000)
        - 美妆个护10% (¥30-¥3,000)
    5. 外键约束：
        - 仓库→门店区域匹配（华北仓库→华北门店）
        - 库存 > 销售数量
        - 补货状态：SHIPPED/DELIVERED/CANCELLED
    6. 生成顺序：
        warehouse → store → product → warehouse_inventory → 
        store_inventory → sales → replenishment → inventory_log
    ##### 表结构参考
    {table_schema}
    """

    batch_size = 50
    total_batches = 40

    for batch in range(1, total_batches + 1):
        # 生成初始SQL
        response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[
                {"role": "system", "content": "您是SQL数据生成专家"},
                {"role": "user", "content": f"{base_prompt}\n\n生成{batch_size}条记录的SQL"}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        initial_sql = response.choices[0].message.content.strip()

        # 检查并修正SQL
        check_prompt = f"""
        ## 检查要求
        请检查以下SQL并修正任何问题：
        1. 是否使用显式VALUES格式（禁用SELECT/UNION）
        2. 日期是否在2024-01-01到2025-06-30均匀分布
        3. 商品比例是否符合要求
        4. 区域是否覆盖全部7大区域
        5. 外键是否合理
        6. 价格区间是否符合类别要求
        7. 生成顺序是否正确

        ## 原始SQL
        {initial_sql}

        请返回修正后的完整SQL（即使没有错误也请返回相同SQL）。
        只需返回SQL代码，不要解释。
        """

        # 获取修正后的SQL
        check_response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[
                {"role": "system", "content": "您是SQL质量检查专家"},
                {"role": "user", "content": check_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        checked_sql = check_response.choices[0].message.content.strip()

        # 保存修正后的SQL
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n-- 批次 {batch} 数据\n")
            f.write(checked_sql)
        print(f"✅ 批次 {batch} 数据已保存")

        # 进度显示
        progress = batch / total_batches * 100
        sys.stdout.write(f"\r进度: [{batch}/{total_batches}] {progress:.1f}%")
        sys.stdout.flush()

        # 添加批次间延迟以避免速率限制
        time.sleep(1)

    print(f"\n生成完成！文件路径: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()