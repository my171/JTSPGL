from typing import List

class DatabaseSchemaAnalyzer:
    """动态数据库模式分析器 - 支持任何PostgreSQL数据库"""    
    def __init__(self, conn):
        self.conn = conn
        self.schema_info = {}
        self.table_relationships = {}
        self.analyze_schema()
    
    def analyze_schema(self):
        """分析数据库模式，获取所有表、字段、关系"""
        cursor = self.conn.cursor()
        try:
            # 1. 获取所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # 2. 获取每个表的字段信息
            for table in tables:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table,))
                
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        'name': row[0],
                        'type': row[1],
                        'nullable': row[2] == 'YES',
                        'default': row[3]
                    })
                
                self.schema_info[table] = columns
            
            # 3. 分析外键关系
            cursor.execute("""
                SELECT 
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_schema = 'public'
            """)
            
            for row in cursor.fetchall():
                table, column, foreign_table, foreign_column = row
                if table not in self.table_relationships:
                    self.table_relationships[table] = []
                self.table_relationships[table].append({
                    'column': column,
                    'foreign_table': foreign_table,
                    'foreign_column': foreign_column
                })
            
        #    print(f"✅ 数据库模式分析完成：发现 {len(tables)} 个表")
        #   for table in tables:
        #       print(f"   📋 {table}: {len(self.schema_info[table])} 个字段")
                
        except Exception as e:
            print(f"❌ 数据库模式分析失败: {e}")
        finally:
            cursor.close()
    
    def get_schema_summary(self) -> str:
        """获取数据库模式摘要"""
        summary = []
        for table, columns in self.schema_info.items():
            col_names = [col['name'] for col in columns]
            summary.append(f"表 {table}: {', '.join(col_names)}")
        return "\n".join(summary)
    
    def find_related_tables(self, table_name: str) -> List[str]:
        """查找与指定表相关的表"""
        related = set()
        if table_name in self.table_relationships:
            for rel in self.table_relationships[table_name]:
                related.add(rel['foreign_table'])
        
        # 反向查找
        for table, rels in self.table_relationships.items():
            for rel in rels:
                if rel['foreign_table'] == table_name:
                    related.add(table)
        
        return list(related)