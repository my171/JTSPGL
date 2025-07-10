#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python db_backup.py backup 备份数据库                                 
#python db_backup.py backup --no-compress 无压缩备份
#python db_backup.py restore /path/to/backup.sql 恢复数据库
#python db_backup.py restore /path/to/backup.sql --force 强制恢复
#python db_backup.py list 列出所有备份

import argparse
import os
import gzip
import time
import configparser
import shutil
import subprocess
import tempfile
import logging
from datetime import datetime
from db_pool import FixedDBPool  # 导入现有的连接池实现

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DBBackupTool')

class DatabaseBackupTool:
    def __init__(self, config_file=r'F:\pycode\JTSPGL\back\services\db_config.ini'):  # 修改配置文件路径
        self.config = self.load_config(config_file)
        self.init_db_pool()
        
    def load_config(self, config_file):
        """加载数据库配置文件"""
        config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            # 创建默认配置文件
            config['DATABASE'] = {
                'type': 'mysql',  # 可以是 'mysql', 'postgres', 'sqlite'
                'host': '127.0.0.1',
                'port': '3306',
                'user': 'root',
                'password': 'DSds178200++',
                'database': 'mysqlddemo',
                'backup_dir': r'F:\pycode\JTSPGL\back\services\backups',  # 更新备份目录路径
                'sqlite_path': r'F:\pycode\JTSPGL\back\services\mysqldemos.db',  # 仅SQLite需要
                'pool_size': '10'  # 连接池大小
            }
            # 确保目录存在
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                config.write(f)
            logger.error(f"配置文件已创建: {config_file}，请修改后重新运行")
            exit(1)
        
        config.read(config_file)
        return config['DATABASE']
    
    def init_db_pool(self):
        """初始化数据库连接池"""
        db_type = self.config['type']
        db_config = {
            'host': self.config['host'],
            'port': int(self.config['port']),
            'user': self.config['user'],
            'password': self.config['password'],
            'database': self.config['database'],
            'maxconn': int(self.config.get('pool_size', 10))
        }
        
        if db_type == 'sqlite':
            db_config['sqlite_path'] = self.config['sqlite_path']
        
        try:
            FixedDBPool.init_pool(db_type=db_type, **db_config)
            logger.info(f"成功初始化 {db_type} 数据库连接池")
        except Exception as e:
            logger.error(f"初始化数据库连接池失败: {str(e)}")
            raise

    def create_backup_dir(self):
        """创建备份目录"""
        backup_dir = self.config['backup_dir']
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            logger.info(f"创建备份目录: {backup_dir}")
        return backup_dir
    
    def backup_database(self, compress=True):
        """备份数据库"""
        logger.info("\n" + "="*50)
        logger.info("开始数据库备份操作")
        logger.info("="*50)
        
        backup_dir = self.create_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_type = self.config['type']
        db_name = self.config['database'] if db_type != 'sqlite' else os.path.basename(self.config['sqlite_path'])
        
        if db_type == 'sqlite':
            return self.backup_sqlite(backup_dir, db_name, timestamp, compress)
        else:
            return self.backup_with_db_tool(backup_dir, db_name, timestamp, compress)
    
    def backup_sqlite(self, backup_dir, db_name, timestamp, compress):
        """备份SQLite数据库"""
        try:
            source_path = self.config['sqlite_path']
            backup_file = os.path.join(
                backup_dir, 
                f"{db_name}_backup_{timestamp}.db"
            )
            
            # 使用连接池确保所有连接已关闭
            FixedDBPool.close_all()
            
            # 复制数据库文件
            shutil.copy2(source_path, backup_file)
            logger.info(f"SQLite数据库已备份到: {backup_file}")
            
            # 压缩备份文件
            if compress:
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(backup_file)
                final_file = compressed_file
                logger.info(f"备份文件已压缩: {final_file}")
            else:
                final_file = backup_file
            
            logger.info(f"备份完成! 文件路径: {final_file}")
            return True
        except Exception as e:
            logger.error(f"SQLite备份失败: {str(e)}")
            return False
    
    def backup_with_db_tool(self, backup_dir, db_name, timestamp, compress):
        """使用数据库工具备份MySQL/PostgreSQL"""
        db_type = self.config['type']
        backup_file = os.path.join(
            backup_dir, 
            f"{db_name}_backup_{timestamp}.sql"
        )
        
        try:
            # 使用连接池执行备份前检查
            with FixedDBPool.get_connection() as conn:
                cursor = conn.cursor()
                if db_type == 'mysql':
                    cursor.execute("SHOW TABLES")
                elif db_type == 'postgres':
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
                tables = cursor.fetchall()
                logger.info(f"检测到 {len(tables)} 张表，开始备份...")
        
            # 构建备份命令
            if db_type == 'mysql':
                backup_cmd = (
                    f"mysqldump --single-transaction --skip-lock-tables "
                    f"-h {self.config['host']} "
                    f"-P {self.config['port']} "
                    f"-u {self.config['user']} "
                    f"-p{self.config['password']} "
                    f"{self.config['database']} > {backup_file}"
                )
            elif db_type == 'postgres':
                backup_cmd = (
                    f"PGPASSWORD={self.config['password']} pg_dump "
                    f"-h {self.config['host']} "
                    f"-p {self.config['port']} "
                    f"-U {self.config['user']} "
                    f"-d {self.config['database']} "
                    f"-f {backup_file}"
                )
            
            # 执行备份命令
            result = subprocess.run(
                backup_cmd, 
                shell=True, 
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 检查备份文件是否生成
            if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
                raise Exception("备份文件创建失败或为空")
            
            logger.info(f"数据库已备份到: {backup_file}")
            
            # 压缩备份文件
            if compress:
                compressed_file = f"{backup_file}.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(backup_file)
                final_file = compressed_file
                logger.info(f"备份文件已压缩: {final_file}")
            else:
                final_file = backup_file
            
            logger.info(f"备份完成! 文件路径: {final_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"备份命令执行失败: {e.stderr.decode().strip()}")
            return False
        except Exception as e:
            logger.error(f"备份失败: {str(e)}")
            return False
    
    def restore_database(self, backup_path, confirm=True):
        """恢复数据库"""
        logger.info("\n" + "="*50)
        logger.info("开始数据库恢复操作 - 这将覆盖现有数据!")
        logger.info("="*50)
        
        if not os.path.exists(backup_path):
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        db_type = self.config['type']
        
        if confirm:
            logger.warning(f"即将恢复数据库: {self.config['database']}")
            logger.warning(f"使用备份文件: {backup_path}")
            confirmation = input("确认执行恢复操作? (y/N): ").strip().lower()
            if confirmation != 'y':
                logger.info("恢复操作已取消")
                return False
        
        if db_type == 'sqlite':
            return self.restore_sqlite(backup_path)
        else:
            return self.restore_with_db_tool(backup_path)
    
    def restore_sqlite(self, backup_path):
        """恢复SQLite数据库"""
        try:
            target_path = self.config['sqlite_path']
            
            # 使用连接池确保所有连接已关闭
            FixedDBPool.close_all()
            
            # 备份当前数据库
            backup_dir = os.path.dirname(target_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_current = os.path.join(backup_dir, f"pre_restore_{timestamp}.db.bak")
            shutil.copy2(target_path, backup_current)
            logger.info(f"当前数据库已备份到: {backup_current}")
            
            # 恢复数据库
            shutil.copy2(backup_path, target_path)
            logger.info(f"数据库已从 {backup_path} 恢复")
            return True
        except Exception as e:
            logger.error(f"SQLite恢复失败: {str(e)}")
            return False
    
    def restore_with_db_tool(self, backup_path):
        """使用数据库工具恢复MySQL/PostgreSQL"""
        db_type = self.config['type']
        temp_file = None
        
        try:
            # 处理压缩文件
            if backup_path.endswith('.gz'):
                logger.info("检测到压缩备份文件，正在解压...")
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sql')
                with gzip.open(backup_path, 'rb') as f_in:
                    temp_file.write(f_in.read())
                temp_file.close()
                restore_file = temp_file.name
                logger.info(f"解压完成，临时文件: {restore_file}")
            else:
                restore_file = backup_path
            
            # 构建恢复命令
            if db_type == 'mysql':
                restore_cmd = (
                    f"mysql -h {self.config['host']} "
                    f"-P {self.config['port']} "
                    f"-u {self.config['user']} "
                    f"-p{self.config['password']} "
                    f"{self.config['database']} < {restore_file}"
                )
            elif db_type == 'postgres':
                restore_cmd = (
                    f"PGPASSWORD={self.config['password']} psql "
                    f"-h {self.config['host']} "
                    f"-p {self.config['port']} "
                    f"-U {self.config['user']} "
                    f"-d {self.config['database']} "
                    f"-f {restore_file}"
                )
            
            # 执行恢复命令
            result = subprocess.run(
                restore_cmd, 
                shell=True, 
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"数据库已从 {backup_path} 恢复")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"恢复命令执行失败: {e.stderr.decode().strip()}")
            return False
        except Exception as e:
            logger.error(f"恢复失败: {str(e)}")
            return False
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                logger.info(f"已清理临时文件: {temp_file.name}")
    
    def list_backups(self):
        """列出所有备份文件"""
        backup_dir = self.config.get('backup_dir', '/var/db_backups')
        if not os.path.exists(backup_dir):
            logger.error(f"备份目录不存在: {backup_dir}")
            return
        
        db_name = self.config['database'] if self.config['type'] != 'sqlite' else os.path.basename(self.config['sqlite_path'])
        
        logger.info(f"备份目录: {backup_dir}")
        files = [f for f in os.listdir(backup_dir) 
                 if f.startswith(db_name) and (f.endswith('.sql') or f.endswith('.gz') or f.endswith('.db'))]
        
        if not files:
            logger.info("没有找到备份文件")
            return
        
        files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
        
        logger.info("\n可用备份文件:")
        logger.info("-" * 70)
        for i, file in enumerate(files):
            file_path = os.path.join(backup_dir, file)
            size = os.path.getsize(file_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            logger.info(f"{i+1}. {file} | {self.format_size(size)} | {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 70)
        return files
    
    @staticmethod
    def format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

def main():
    parser = argparse.ArgumentParser(description='数据库备份与恢复工具 (使用连接池)')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--no-compress', action='store_true', help='不压缩备份文件')
    
    # 恢复命令
    restore_parser = subparsers.add_parser('restore', help='恢复数据库')
    restore_parser.add_argument('file', nargs='?', help='备份文件路径')
    restore_parser.add_argument('--force', action='store_true', help='跳过确认提示')
    
    # 列出备份命令
    subparsers.add_parser('list', help='列出所有备份文件')
    
    args = parser.parse_args()
    
    try:
        # 使用新的配置文件路径
        config_path = r'F:\pycode\JTSPGL\back\services\db_config.ini'
        tool = DatabaseBackupTool(config_file=config_path)
        
        if args.command == 'backup':
            tool.backup_database(compress=not args.no_compress)
        elif args.command == 'restore':
            if args.file:
                tool.restore_database(args.file, confirm=not args.force)
            else:
                logger.info("请指定要恢复的备份文件")
                files = tool.list_backups()
                if files:
                    choice = input("请输入要恢复的备份文件编号: ")
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(files):
                            backup_path = os.path.join(tool.config['backup_dir'], files[index])
                            tool.restore_database(backup_path, confirm=not args.force)
                        else:
                            logger.error("无效的选择")
                    except ValueError:
                        logger.error("请输入有效数字")
        elif args.command == 'list':
            tool.list_backups()
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()