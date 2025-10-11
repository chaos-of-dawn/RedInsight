"""
数据打包脚本 - 将抓取的Reddit数据打包成大模型可处理的文件
支持按抓取会话、时间范围、子版块等条件进行数据打包
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from database import DatabaseManager
from llm_analyzer import LLMAnalyzer
from data_organizer import DataOrganizer
from config import Config

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data_packaging.log', encoding='utf-8')
        ]
    )

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Reddit数据打包工具')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--subreddits', type=str, nargs='+', help='子版块列表')
    parser.add_argument('--format', type=str, choices=['json', 'txt', 'markdown'], 
                       default='json', help='输出格式')
    parser.add_argument('--output-dir', type=str, default='output', help='输出目录')
    parser.add_argument('--include-metadata', action='store_true', 
                       help='包含元数据')
    parser.add_argument('--use-llm', action='store_true', 
                       help='使用LLM生成精准内容梗概')
    parser.add_argument('--llm-provider', type=str, 
                       choices=['openai', 'anthropic', 'deepseek'], 
                       default='openai', help='LLM提供商')
    
    args = parser.parse_args()
    
    try:
        # 初始化组件
        logger.info("初始化数据库和LLM分析器...")
        db_manager = DatabaseManager()
        
        llm_analyzer = None
        if args.use_llm:
            try:
                llm_analyzer = LLMAnalyzer()
                logger.info("LLM分析器初始化成功")
            except Exception as e:
                logger.warning(f"LLM分析器初始化失败: {str(e)}")
                logger.info("将使用简单摘要方法")
        
        # 创建数据整理器
        organizer = DataOrganizer(db_manager, llm_analyzer)
        
        # 整理数据
        logger.info("开始整理数据...")
        organized_data = organizer.organize_data_by_scraping_session(
            start_date=args.start_date,
            end_date=args.end_date,
            subreddits=args.subreddits
        )
        
        if "error" in organized_data:
            logger.error(f"数据整理失败: {organized_data['error']}")
            return 1
        
        # 创建数据包
        logger.info(f"创建{args.format.upper()}格式数据包...")
        package_content = organizer.create_llm_ready_package(
            organized_data,
            output_format=args.format,
            include_metadata=args.include_metadata
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reddit_data_{timestamp}.{args.format}"
        
        # 保存文件
        logger.info(f"保存数据包到 {args.output_dir}/{filename}...")
        file_path = organizer.save_package_to_file(
            package_content,
            filename,
            args.output_dir
        )
        
        # 显示统计信息
        metadata = organized_data.get('metadata', {})
        logger.info("=" * 60)
        logger.info("数据打包完成!")
        logger.info(f"文件路径: {file_path}")
        logger.info(f"总分组数: {metadata.get('total_groups', 0)}")
        logger.info(f"总帖子数: {metadata.get('total_posts', 0)}")
        logger.info(f"总评论数: {metadata.get('total_comments', 0)}")
        logger.info(f"涉及子版块: {', '.join(metadata.get('subreddits', []))}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"数据打包失败: {str(e)}")
        return 1

def interactive_mode():
    """交互式模式"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("Reddit数据打包工具 - 交互式模式")
    print("=" * 60)
    
    try:
        # 初始化组件
        print("初始化数据库...")
        db_manager = DatabaseManager()
        
        # 检查是否有数据
        stats = db_manager.get_analysis_statistics()
        if stats.get('total_posts', 0) == 0:
            print("❌ 数据库中没有帖子数据，请先进行数据抓取")
            return 1
        
        print(f"✅ 数据库中有 {stats.get('total_posts', 0)} 个帖子")
        
        # 获取可用的子版块
        subreddits = db_manager.get_subreddit_list()
        print(f"📋 可用的子版块: {', '.join(subreddits)}")
        
        # 用户输入
        print("\n请选择数据范围:")
        
        # 日期范围
        start_date = input("开始日期 (YYYY-MM-DD，留空表示不限制): ").strip()
        if start_date and not _validate_date(start_date):
            print("❌ 日期格式错误，使用默认值")
            start_date = None
        
        end_date = input("结束日期 (YYYY-MM-DD，留空表示不限制): ").strip()
        if end_date and not _validate_date(end_date):
            print("❌ 日期格式错误，使用默认值")
            end_date = None
        
        # 子版块选择
        print(f"\n可用的子版块: {', '.join(subreddits)}")
        subreddit_input = input("选择子版块 (用空格分隔，留空表示全部): ").strip()
        selected_subreddits = subreddit_input.split() if subreddit_input else None
        
        # 输出格式
        print("\n输出格式:")
        print("1. JSON (推荐)")
        print("2. TXT")
        print("3. Markdown")
        format_choice = input("选择格式 (1-3，默认1): ").strip()
        format_map = {'1': 'json', '2': 'txt', '3': 'markdown'}
        output_format = format_map.get(format_choice, 'json')
        
        # 是否包含元数据
        include_meta = input("包含元数据? (y/N): ").strip().lower() == 'y'
        
        # 是否使用LLM
        use_llm = input("使用LLM生成精准梗概? (y/N): ").strip().lower() == 'y'
        
        # 初始化LLM分析器
        llm_analyzer = None
        if use_llm:
            try:
                llm_analyzer = LLMAnalyzer()
                print("✅ LLM分析器初始化成功")
            except Exception as e:
                print(f"⚠️ LLM分析器初始化失败: {str(e)}")
                print("将使用简单摘要方法")
        
        # 创建数据整理器
        organizer = DataOrganizer(db_manager, llm_analyzer)
        
        # 整理数据
        print("\n开始整理数据...")
        organized_data = organizer.organize_data_by_scraping_session(
            start_date=start_date,
            end_date=end_date,
            subreddits=selected_subreddits
        )
        
        if "error" in organized_data:
            print(f"❌ 数据整理失败: {organized_data['error']}")
            return 1
        
        # 创建数据包
        print(f"创建{output_format.upper()}格式数据包...")
        package_content = organizer.create_llm_ready_package(
            organized_data,
            output_format=output_format,
            include_metadata=include_meta
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reddit_data_{timestamp}.{output_format}"
        
        # 保存文件
        print(f"保存数据包到 output/{filename}...")
        file_path = organizer.save_package_to_file(
            package_content,
            filename,
            "output"
        )
        
        # 显示结果
        metadata = organized_data.get('metadata', {})
        print("\n" + "=" * 60)
        print("✅ 数据打包完成!")
        print(f"📁 文件路径: {file_path}")
        print(f"📊 总分组数: {metadata.get('total_groups', 0)}")
        print(f"📝 总帖子数: {metadata.get('total_posts', 0)}")
        print(f"💬 总评论数: {metadata.get('total_comments', 0)}")
        print(f"📍 涉及子版块: {', '.join(metadata.get('subreddits', []))}")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
        return 1
    except Exception as e:
        print(f"\n❌ 数据打包失败: {str(e)}")
        return 1

def _validate_date(date_string: str) -> bool:
    """验证日期格式"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 没有命令行参数，进入交互式模式
        sys.exit(interactive_mode())
    else:
        # 使用命令行参数
        sys.exit(main())
