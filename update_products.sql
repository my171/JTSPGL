
-- 导出整个数据库 mysqldemo 的所有表结构和数据
SET @DATABASE_NAME = 'mysqldemo';

-- 禁用外键检查确保导入顺利
SET FOREIGN_KEY_CHECKS = 0;

-- 获取所有表名
SET @tables = NULL;
SELECT GROUP_CONCAT(table_schema, '.', table_name) INTO @tables
  FROM information_schema.tables 
  WHERE table_schema = @DATABASE_NAME;

-- 动态生成导出脚本
SET @tables = IFNULL(@tables, CONCAT(@DATABASE_NAME, '.no_tables_found'));
SET @output_sql = NULL;

SELECT GROUP_CONCAT(
  CONCAT(
    'SELECT "导出表: ', table_name, '" AS `INFO`; ',
    'SHOW CREATE TABLE `', table_name, '`; ',
    'SELECT * FROM `', table_name, '`; '
  ) SEPARATOR '\n'
) INTO @output_sql
FROM information_schema.tables
WHERE table_schema = @DATABASE_NAME;

-- 如果数据库为空则输出提示
SET @output_sql = IFNULL(@output_sql, 'SELECT "数据库为空" AS `INFO`;');

-- 准备并执行动态SQL
PREPARE stmt FROM @output_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;
```

**说明：**  
此SQL文件执行后将完整输出 `mysqldemo` 数据库的：
1. 每个表的名称（`INFO` 标记）
2. 表结构（通过 `SHOW CREATE TABLE`）
3. 所有数据行（通过 `SELECT *`）

执行流程：
1. 动态获取数据库所有表名
2. 为每个表生成包含表名、建表语句、完整数据的查询
3. 一次性输出所有内容（注释行仅作说明，实际执行时不会输出）