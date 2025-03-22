import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_db_structure():
    """Check database structure"""
    connection_string = os.getenv('DB_CONNECTION_STRING')
    
    if not connection_string:
        print("Missing DB_CONNECTION_STRING environment variable")
        return
    
    try:
        # Connect to database
        print(f"Connecting to database...")
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        print(f"Connected successfully!")
        
        # Get all tables
        cursor.execute("""
        SELECT table_name = t.name
        FROM sys.tables t
        ORDER BY t.name
        """)
        
        tables = [row.table_name for row in cursor.fetchall()]
        print(f"\nFound {len(tables)} tables in database:")
        for table in tables:
            print(f"  - {table}")
        
        # Check each table structure
        for table in tables:
            print(f"\n===== Table: {table} =====")
            
            # Get columns
            cursor.execute(f"""
            SELECT 
                c.name as column_name,
                t.name as data_type,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                CASE WHEN pk.is_primary_key = 1 THEN 'PK' ELSE '' END as is_primary_key
            FROM 
                sys.columns c
            JOIN 
                sys.types t ON c.user_type_id = t.user_type_id
            LEFT JOIN (
                SELECT 
                    ic.object_id,
                    ic.column_id,
                    1 as is_primary_key
                FROM 
                    sys.indexes i
                JOIN 
                    sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                WHERE 
                    i.is_primary_key = 1
            ) pk ON c.object_id = pk.object_id AND c.column_id = pk.column_id
            WHERE 
                c.object_id = OBJECT_ID('{table}')
            ORDER BY 
                c.column_id
            """)
            
            columns = cursor.fetchall()
            print(f"Columns:")
            for col in columns:
                nullable = "NULL" if col.is_nullable else "NOT NULL"
                data_type = col.data_type
                if data_type in ('nvarchar', 'varchar', 'char', 'nchar'):
                    if col.max_length == -1:
                        data_type += "(MAX)"
                    elif data_type.startswith('n'):  # Unicode types, divide length by 2
                        data_type += f"({col.max_length // 2})"
                    else:
                        data_type += f"({col.max_length})"
                elif data_type in ('decimal', 'numeric'):
                    data_type += f"({col.precision},{col.scale})"
                    
                pk_flag = "PK" if col.is_primary_key else ""
                print(f"  {col.column_name} {data_type} {nullable} {pk_flag}")
            
            # Get foreign keys
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
                fk.parent_object_id = OBJECT_ID('{table}')
            """)
            
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print("\nForeign Keys:")
                for fk in foreign_keys:
                    print(f"  {fk.fk_name}: {fk.parent_column} -> {fk.referenced_table}({fk.referenced_column})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking database structure: {e}")

if __name__ == "__main__":
    check_db_structure() 