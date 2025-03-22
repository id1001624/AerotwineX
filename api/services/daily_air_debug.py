#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging
import os
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailyAirDebug')

def save_html(url, filename="webpage.html"):
    """保存网页HTML到文件以便分析"""
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # 发送请求
        logger.info(f"正在获取网页: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 保存响应内容
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"网页内容已保存至: {filename}")
        
        return response.text
    except Exception as e:
        logger.error(f"获取网页时出错: {e}")
        return None

def analyze_tables(html_content):
    """分析HTML中的表格结构"""
    if not html_content:
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有表格
    tables = soup.find_all('table')
    logger.info(f"找到 {len(tables)} 个表格")
    
    # 分析每个表格
    for i, table in enumerate(tables):
        logger.info(f"\n表格 {i+1}:")
        
        # 查找表格的前一个元素，以获取表格标题或描述
        prev_element = table.find_previous_sibling()
        if prev_element:
            logger.info(f"前一个元素: {prev_element.name} - 内容: {prev_element.text.strip()[:50]}...")
        
        # 尝试获取表格的父元素或容器
        parent = table.parent
        if parent:
            logger.info(f"父元素: {parent.name} - 类名: {parent.get('class', '无类名')}")
        
        # 分析表格结构
        rows = table.find_all('tr')
        logger.info(f"行数: {len(rows)}")
        
        # 查看表头
        header_row = table.find('tr')
        if header_row:
            headers = header_row.find_all(['th', 'td'])
            header_text = [h.text.strip() for h in headers]
            logger.info(f"表头: {header_text}")
        
        # 示例数据行
        if len(rows) > 1:
            sample_row = rows[1]
            cells = sample_row.find_all(['th', 'td'])
            cell_text = [c.text.strip() for c in cells]
            logger.info(f"示例数据行: {cell_text}")

def find_route_elements(html_content):
    """查找页面中的航线元素"""
    if not html_content:
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找可能包含航线信息的元素
    route_keywords = ['台東蘭嶼', '蘭嶼台東', '台東綠島', '綠島台東', '高雄七美', '七美高雄', 
                      '七美澎湖', '澎湖七美', '高雄望安', '望安高雄']
    
    for keyword in route_keywords:
        elements = soup.find_all(string=lambda text: keyword in text if text else False)
        if elements:
            logger.info(f"\n找到 {len(elements)} 个包含 '{keyword}' 的元素:")
            for element in elements[:3]:  # 只显示前3个
                parent = element.parent
                logger.info(f"元素: {parent.name} - 内容: {element[:50]}...")
                # 找到这个元素后的表格
                next_table = parent.find_next('table')
                if next_table:
                    rows = next_table.find_all('tr')
                    logger.info(f"  后面的表格有 {len(rows)} 行")
                    # 打印表格的一些样本数据
                    if len(rows) > 1:
                        cells = rows[1].find_all(['th', 'td'])
                        cell_text = [c.text.strip() for c in cells]
                        logger.info(f"  表格样本数据: {cell_text}")

def main():
    """主函数"""
    # 德安航空网站URL
    url = "https://www.dailyair.com.tw/dailyair/page/FlightTime/"
    
    # 保存HTML到文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_filename = f"daily_air_html_{timestamp}.html"
    html_content = save_html(url, html_filename)
    
    if html_content:
        # 分析表格结构
        logger.info("\n=== 表格分析 ===")
        analyze_tables(html_content)
        
        # 查找航线元素
        logger.info("\n=== 航线元素查找 ===")
        find_route_elements(html_content)
        
        logger.info("\n=== 分析完成 ===")
        logger.info(f"详细HTML已保存至 {html_filename} 以供进一步分析")

if __name__ == "__main__":
    main() 