import os
import pyodbc
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_table_structure(table_name):
    """检查指定表的结构"""
    connection_string = os.getenv('DB_CONNECTION_STRING')
    
    if not connection_string:
        print("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
        return
    
    try:
        # 连接数据库
        print(f"尝试连接数据库...")
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        print(f"数据库连接成功!")
        
        # 检查表是否存在
        cursor.execute(f"SELECT OBJECT_ID('{table_name}', 'U')")
        table_exists = cursor.fetchone()[0] is not None
        
        if not table_exists:
            print(f"表 {table_name} 不存在!")
            return
        
        # 获取表结构
        cursor.execute(f"""
        SELECT 
            c.name as column_name,
            t.name as data_type,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable
        FROM 
            sys.columns c
        JOIN 
            sys.types t ON c.user_type_id = t.user_type_id
        WHERE 
            c.object_id = OBJECT_ID('{table_name}')
        ORDER BY 
            c.column_id
        """)
        
        columns = cursor.fetchall()
        print(f"\n表 {table_name} 的结构:")
        for col in columns:
            nullable = "NULL" if col.is_nullable else "NOT NULL"
            data_type = col.data_type
            if data_type in ('nvarchar', 'varchar', 'char', 'nchar'):
                if col.max_length == -1:
                    data_type += "(MAX)"
                elif data_type.startswith('n'):  # Unicode类型，长度要除以2
                    data_type += f"({col.max_length // 2})"
                else:
                    data_type += f"({col.max_length})"
            elif data_type in ('decimal', 'numeric'):
                data_type += f"({col.precision},{col.scale})"
                
            print(f"  {col.column_name} {data_type} {nullable}")
        
        # 获取主键信息
        cursor.execute(f"""
        SELECT 
            i.name as index_name,
            COL_NAME(ic.object_id, ic.column_id) as column_name
        FROM 
            sys.indexes i
        JOIN 
            sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        WHERE 
            i.object_id = OBJECT_ID('{table_name}') AND
            i.is_primary_key = 1
        """)
        
        primary_keys = cursor.fetchall()
        if primary_keys:
            print("\n主键:")
            for pk in primary_keys:
                print(f"  {pk.index_name} ({pk.column_name})")
        
        # 获取外键信息
        cursor.execute(f"""
        SELECT 
            fk.name as fk_name,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) as parent_column,
            OBJECT_NAME(fkc.referenced_object_id) as referenced_table,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) as referenced_column
        FROM 
            sys.foreign_keys fk
        JOIN 
            sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        WHERE 
            fk.parent_object_id = OBJECT_ID('{table_name}')
        """)
        
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            print("\n外键:")
            for fk in foreign_keys:
                print(f"  {fk.fk_name}: {fk.parent_column} -> {fk.referenced_table}({fk.referenced_column})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"查询表结构时出错: {e}")

if __name__ == "__main__":
    # 检查航班相关表
    tables = ['Airports', 'Airlines', 'Flights', 'TempFlights']
    for table in tables:
        check_table_structure(table)
        print("\n" + "-"*50 + "\n") 