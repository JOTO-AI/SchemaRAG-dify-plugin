"""
图表生成模块
"""

import json
import logging
from typing import Any, Dict, List

import requests

from .config import ChartConfig
from .data_processor import DataProcessor
from .models import ChartRecommendation

logger = logging.getLogger(__name__)


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self):
        """初始化图表生成器"""
        self.config = ChartConfig()
        self.data_processor = DataProcessor()
    
    def generate_chart_config(
        self,
        recommendation: ChartRecommendation,
        data: List[Dict]
    ) -> Dict[str, Any]:
        """
        根据推荐生成图表配置
        
        Args:
            recommendation: 图表推荐
            data: 原始数据
            
        Returns:
            完整的图表配置
        """
        # 转换数据为图表所需格式
        chart_data = self.data_processor.transform_data_for_chart(
            recommendation.chart_type,
            data,
            recommendation.x_field,
            recommendation.y_field
        )
        
        # 根据图表类型生成配置
        if recommendation.chart_type == "line":
            return self._generate_line_config(recommendation, chart_data)
        elif recommendation.chart_type == "histogram":
            return self._generate_histogram_config(recommendation, chart_data, data)
        elif recommendation.chart_type == "pie":
            return self._generate_pie_config(recommendation, chart_data)
        else:
            raise ValueError(f"不支持的图表类型: {recommendation.chart_type}")
    
    def _generate_line_config(
        self,
        recommendation: ChartRecommendation,
        chart_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        生成折线图配置
        
        Args:
            recommendation: 图表推荐
            chart_data: 图表数据
            
        Returns:
            折线图配置
        """
        return self.config.create_chart_config(
            chart_type="line",
            data=chart_data,
            title=recommendation.title,
            x_title=recommendation.x_field,
            y_title=recommendation.y_field or "",
            style={
                **ChartConfig.BASE_CONFIG["style"],
                "lineWidth": 3
            },
            stack=False
        )
    
    def _generate_histogram_config(
        self,
        recommendation: ChartRecommendation,
        chart_data: List[float],
        original_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        生成直方图配置
        
        Args:
            recommendation: 图表推荐
            chart_data: 图表数据
            original_data: 原始数据
            
        Returns:
            直方图配置
        """
        bin_number = min(10, len(original_data) // 5) or 5
        
        return self.config.create_chart_config(
            chart_type="histogram",
            data=chart_data,
            title=recommendation.title,
            x_title=f"{recommendation.y_field or recommendation.x_field}区间",
            y_title="数量",
            binNumber=bin_number,
            style={
                **ChartConfig.BASE_CONFIG["style"],
                "backgroundColor": "#f6f8fa"
            }
        )
    
    def _generate_pie_config(
        self,
        recommendation: ChartRecommendation,
        chart_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        生成饼图配置
        
        Args:
            recommendation: 图表推荐
            chart_data: 图表数据
            
        Returns:
            饼图配置
        """
        return self.config.create_chart_config(
            chart_type="pie",
            data=chart_data,
            title=recommendation.title,
            innerRadius=0.5,
            style=ChartConfig.BASE_CONFIG["style"],
            width=800,
            height=600
        )
    
    def generate_chart_url(self, config: Dict[str, Any]) -> str:
        """
        调用 AntV API 生成图表并返回 URL
        
        Args:
            config: 图表配置
            
        Returns:
            图表 URL
            
        Raises:
            ValueError: 生成图表失败时抛出
        """
        try:
            logger.debug(f"发送图表配置到 AntV: {json.dumps(config, ensure_ascii=False)}")
            
            response = requests.post(
                ChartConfig.ANTV_API_URL,
                json=config,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'User-Agent': 'Dify-Plugin-Visualization/1.0'
                },
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()
            
            logger.debug(f"AntV 响应: {json.dumps(response_data, ensure_ascii=False)}")
            
            # 检查响应状态
            if 'success' in response_data and not response_data['success']:
                error_msg = response_data.get('errorMessage', '未知错误')
                raise ValueError(f"AntV API 返回错误: {error_msg}")
            
            # 从 resultObj 字段获取 URL
            if 'resultObj' in response_data and isinstance(response_data['resultObj'], str):
                return response_data['resultObj']
            
            raise ValueError("AntV API 响应中未找到有效的图表 URL")
            
        except requests.exceptions.Timeout:
            logger.error("请求 AntV API 超时")
            raise ValueError("请求 AntV API 超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"请求 AntV API 失败: {str(e)}")
            raise ValueError(f"请求 AntV API 失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"解析 AntV 响应失败: {str(e)}\n响应内容: {response.text}")
            raise ValueError(f"解析 AntV 响应失败: {str(e)}")
        except Exception as e:
            logger.error(f"生成图表时发生错误: {str(e)}")
            raise ValueError(f"生成图表时发生错误: {str(e)}")
    
    def generate(
        self,
        recommendation: ChartRecommendation,
        data: List[Dict]
    ) -> str:
        """
        生成图表的完整流程
        
        Args:
            recommendation: 图表推荐
            data: 原始数据
            
        Returns:
            图表 URL
        """
        # 1. 生成图表配置
        config = self.generate_chart_config(recommendation, data)
        
        # 2. 调用 API 生成图表
        chart_url = self.generate_chart_url(config)
        
        return chart_url