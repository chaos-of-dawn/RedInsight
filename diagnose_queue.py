"""
诊断任务队列状态
检查为什么没有待执行任务
"""
import sqlite3
from datetime import datetime
from collections import Counter

def diagnose_queue(db_path='redinsight.db'):
    """诊断任务队列状态"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("任务队列诊断报告")
        print("=" * 60)
        print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. 检查所有任务的状态分布
        print("1. 任务状态分布:")
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM auto_interaction_queue 
            GROUP BY status
        """)
        status_dist = cursor.fetchall()
        if status_dist:
            for status, count in status_dist:
                print(f"   - {status}: {count} 个")
        else:
            print("   - 数据库中没有任务记录")
        print()
        
        # 2. 检查审核状态分布
        print("2. 审核状态分布:")
        cursor.execute("""
            SELECT review_status, COUNT(*) as count 
            FROM auto_interaction_queue 
            GROUP BY review_status
        """)
        review_dist = cursor.fetchall()
        if review_dist:
            for review_status, count in review_dist:
                status_str = review_status if review_status else "NULL (无需审核)"
                print(f"   - {status_str}: {count} 个")
        else:
            print("   - 没有任务记录")
        print()
        
        # 3. 检查需要审核但未审核的任务
        print("3. 需要审核但未审核的任务:")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM auto_interaction_queue 
            WHERE requires_review = 1 
            AND review_status = 'pending'
            AND status = 'pending'
        """)
        pending_review = cursor.fetchone()[0]
        print(f"   - 待审核任务: {pending_review} 个")
        if pending_review > 0:
            print("   ⚠️  有任务需要人工审核才能执行！")
        print()
        
        # 4. 检查符合执行条件的任务（应该被查询到的任务）
        print("4. 符合执行条件的任务（status='pending' 且 (review_status='approved' 或 review_status IS NULL)):")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM auto_interaction_queue 
            WHERE status = 'pending'
            AND (review_status = 'approved' OR review_status IS NULL)
        """)
        executable = cursor.fetchone()[0]
        print(f"   - 可执行任务: {executable} 个")
        if executable == 0:
            print("   ⚠️  没有可执行的任务！")
        print()
        
        # 5. 检查最近创建的任务（前10个）
        print("5. 最近创建的任务（前10个）:")
        cursor.execute("""
            SELECT id, post_id, subreddit, interaction_type, status, 
                   requires_review, review_status, post_score, created_at
            FROM auto_interaction_queue 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_tasks = cursor.fetchall()
        if recent_tasks:
            print("   ID | 帖子ID | 子版块 | 类型 | 状态 | 需审核 | 审核状态 | 评分 | 创建时间")
            print("   " + "-" * 100)
            for task in recent_tasks:
                task_id, post_id, subreddit, inter_type, status, req_review, rev_status, score, created_at = task
                req_review_str = "是" if req_review else "否"
                rev_status_str = rev_status if rev_status else "NULL"
                post_id_short = post_id[:8] + "..." if len(post_id) > 8 else post_id
                print(f"   {task_id:3d} | {post_id_short:8s} | r/{subreddit[:15]:15s} | {inter_type:6s} | {status:8s} | {req_review_str:4s} | {rev_status_str:8s} | {score:5.2f} | {created_at}")
        else:
            print("   - 没有任务记录")
        print()
        
        # 6. 检查被拒绝的任务
        print("6. 被拒绝的任务:")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM auto_interaction_queue 
            WHERE review_status = 'rejected'
        """)
        rejected = cursor.fetchone()[0]
        print(f"   - 被拒绝任务: {rejected} 个")
        print()
        
        # 7. 检查已完成的任务
        print("7. 已完成的任务:")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM auto_interaction_queue 
            WHERE status = 'completed'
        """)
        completed = cursor.fetchone()[0]
        print(f"   - 已完成任务: {completed} 个")
        print()
        
        # 8. 检查失败的任务
        print("8. 失败的任务:")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM auto_interaction_queue 
            WHERE status = 'failed'
        """)
        failed = cursor.fetchone()[0]
        print(f"   - 失败任务: {failed} 个")
        if failed > 0:
            print("   最近失败的5个任务:")
            cursor.execute("""
                SELECT id, subreddit, error_message, created_at
                FROM auto_interaction_queue 
                WHERE status = 'failed'
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            failed_tasks = cursor.fetchall()
            for task in failed_tasks:
                task_id, subreddit, error_msg, created_at = task
                error_short = error_msg[:50] + "..." if error_msg and len(error_msg) > 50 else (error_msg or "无错误信息")
                print(f"   - 任务 #{task_id} (r/{subreddit}): {error_short}")
        print()
        
        # 9. 总结和建议
        print("=" * 60)
        print("诊断总结:")
        print("=" * 60)
        
        if executable == 0:
            if pending_review > 0:
                print("⚠️  问题: 有任务需要人工审核，但审核状态为 'pending'")
                print("   建议: 前往'自动运营'页面的'待审核评论'区域，审核并批准这些任务")
            elif status_dist:
                # 检查是否有任务但状态不对
                all_tasks = sum(count for _, count in status_dist)
                if all_tasks > 0:
                    print(f"⚠️  问题: 数据库中有 {all_tasks} 个任务，但没有可执行的任务")
                    print("   可能原因:")
                    print("   1. 所有任务都需要审核但未审核")
                    print("   2. 所有任务的状态不是 'pending'")
                    print("   3. 所有任务都被拒绝了")
                    print("   建议: 检查任务状态，重置需要执行的任务状态为 'pending'")
                else:
                    print("ℹ️  数据库中没有任务记录")
                    print("   建议: 在'自动运营'页面输入关键词搜索帖子，系统会自动评分并加入队列")
            else:
                print("ℹ️  数据库中没有任务记录")
                print("   建议: 在'自动运营'页面输入关键词搜索帖子，系统会自动评分并加入队列")
        else:
            print(f"✅ 有 {executable} 个可执行任务")
            print("   如果系统显示0个任务，可能是:")
            print("   1. 查询逻辑问题")
            print("   2. 数据库连接问题")
            print("   3. 时间不在执行时间段内")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_queue()



