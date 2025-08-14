"""
LLM 智能绘图主控制器
端到端的图表生成逻辑流程
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .chart_schema import validate_chart_config, SUPPORTED_CHART_TYPES
from .chart_generator import ChartGenerator
from .chart_prompts import create_chart_prompt

# 配置日志
logger = logging.getLogger(__name__)


class LLMChartController:
    """LLM 图表生成控制器"""
    
    def __init__(self, 
                 llm_client=None,
                 output_dir: str = "output/charts",
                 fallback_enabled: bool = True):
        """
        初始化控制器
        
        Args:
            llm_client: LLM 客户端（支持 chat 方法）
            output_dir: 图表输出目录
            fallback_enabled: 是否启用降级方案
        """
        self.llm_client = llm_client
        self.chart_generator = ChartGenerator(output_dir)
        self.fallback_enabled = fallback_enabled
        
    def generate_chart_from_data(self,
                                user_question: str,
                                query_data: Any,
                                additional_context: Optional[str] = None,
                                ) -> Dict[str, Any]:
        """
        从用户问题和数据生成图表
        
        Args:
            user_question: 用户的原始问题
            query_data: NL2SQL 返回的数据
            additional_context: 额外的上下文信息

            
        Returns:
            Dict: 包含生成结果的字典
            {
                "success": bool,
                "chart_path": str,  # 成功时的图表文件路径
                "chart_config": dict,  # 使用的图表配置
                "error": str,  # 失败时的错误信息
                "fallback_data": Any  # 降级方案的数据
            }
        """
        result = {
            "success": False,
            "chart_path": None,
            "chart_config": None,
            "error": None,
            "fallback_data": None
        }
        
        try:
            # 第1步：检查 LLM 客户端
            if not self.llm_client:
                raise ValueError("LLM 客户端未配置")
            
            # 第2步：生成 Prompt
            prompt = create_chart_prompt(
                user_question=user_question,
                query_data=query_data,
                additional_context=additional_context
            )
            
            logger.info("正在调用 LLM 生成图表配置...")
            
            # 第3步：调用 LLM
            llm_response = self._call_llm(prompt)
            
            # 第4步：解析和验证 LLM 响应
            chart_config = self._parse_llm_response(llm_response)
            
            # 第5步：业务逻辑校验
            validated_config = validate_chart_config(chart_config)
            
            # 第6步：生成图表
            chart_path = self.chart_generator.generate_chart(chart_config)
            
            result.update({
                "success": True,
                "chart_path": chart_path,
                "chart_config": chart_config
            })
            
            logger.info(f"图表生成成功: {chart_path}")
            
        except Exception as e:
            error_msg = f"图表生成失败: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            
            # 降级方案
            if self.fallback_enabled:
                result["fallback_data"] = self._create_fallback_data(query_data)
                logger.info("已启用降级方案：返回表格数据")
        
        return result
    
    def generate_chart_from_config(self, chart_config: Dict) -> Dict[str, Any]:
        """
        直接从配置生成图表（跳过 LLM）
        
        Args:
            chart_config: 图表配置字典
            
        Returns:
            Dict: 生成结果
        """
        result = {
            "success": False,
            "chart_path": None,
            "chart_config": None,
            "error": None
        }
        
        try:
            # 验证配置
            validated_config = validate_chart_config(chart_config)
            
            # 生成图表
            chart_path = self.chart_generator.generate_chart(chart_config)
            
            result.update({
                "success": True,
                "chart_path": chart_path,
                "chart_config": chart_config
            })
            
        except Exception as e:
            result["error"] = f"图表生成失败: {str(e)}"
            
        return result
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM API
        
        Args:
            prompt: 输入 Prompt
            
        Returns:
            str: LLM 响应
        """
        try:
            # 假设 LLM 客户端有 chat 方法
            if hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat(prompt)
            elif hasattr(self.llm_client, 'invoke'):
                response = self.llm_client.invoke(prompt)
            elif hasattr(self.llm_client, 'predict'):
                response = self.llm_client.predict(prompt)
            else:
                # 尝试直接调用
                response = self.llm_client(prompt)
            
            return str(response)
            
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {str(e)}")
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        解析 LLM 响应，提取 JSON 配置
        
        Args:
            response: LLM 的原始响应
            
        Returns:
            Dict: 解析后的配置字典
        """
        try:
            # 清理响应文本
            cleaned_response = self._clean_llm_response(response)
            
            # 尝试直接解析
            try:
                config = json.loads(cleaned_response)
                return config
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取 JSON 部分
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    config = json.loads(json_match.group())
                    return config
                else:
                    raise ValueError("响应中未找到有效的 JSON")
                    
        except Exception as e:
            raise ValueError(f"LLM 响应解析失败: {str(e)}\n原始响应: {response}")
    
    def _clean_llm_response(self, response: str) -> str:
        """
        清理 LLM 响应文本
        
        Args:
            response: 原始响应
            
        Returns:
            str: 清理后的响应
        """
        # 移除可能的代码块标记
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # 移除多余的空白
        response = response.strip()
        
        # 移除可能的解释文字（保留 JSON 部分）
        lines = response.split('\n')
        json_start = -1
        json_end = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_start = i
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().endswith('}'):
                json_end = i
                break
        
        if json_start != -1 and json_end != -1:
            json_lines = lines[json_start:json_end + 1]
            response = '\n'.join(json_lines)
        
        return response
    
    def _create_fallback_data(self, query_data: Any) -> Dict:
        """
        创建降级方案数据（表格形式）
        
        Args:
            query_data: 原始查询数据
            
        Returns:
            Dict: 表格数据
        """
        try:
            if isinstance(query_data, list) and len(query_data) > 0:
                # 如果是字典列表，转换为表格格式
                if isinstance(query_data[0], dict):
                    headers = list(query_data[0].keys())
                    rows = [[item.get(key, '') for key in headers] for item in query_data]
                    return {
                        "type": "table",
                        "headers": headers,
                        "rows": rows,
                        "message": "图表生成失败，以表格形式展示数据"
                    }
            
            # 其他情况直接返回原数据
            return {
                "type": "raw",
                "data": query_data,
                "message": "图表生成失败，以原始数据展示"
            }
            
        except Exception:
            return {
                "type": "error",
                "message": "无法创建降级展示方案"
            }


class LLMChartService:
    """LLM 图表服务（单例模式）"""
    
    _instance = None
    _controller = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, llm_client=None, output_dir: str = "output/charts"):
        """初始化服务"""
        self._controller = LLMChartController(
            llm_client=llm_client,
            output_dir=output_dir
        )
    
    def generate_chart(self,
                      user_question: str,
                      query_data: Any,
                      additional_context: Optional[str] = None) -> Dict[str, Any]:
        """生成图表"""
        if not self._controller:
            raise RuntimeError("LLM 图表服务未初始化")
        
        return self._controller.generate_chart_from_data(
            user_question=user_question,
            query_data=query_data,
            additional_context=additional_context
        )
    
    def get_supported_chart_types(self) -> List[str]:
        """获取支持的图表类型"""
        return SUPPORTED_CHART_TYPES.copy()


# 全局服务实例
chart_service = LLMChartService()


# 便捷函数
def initialize_chart_service(llm_client=None, output_dir: str = "output/charts"):
    """初始化图表服务"""
    chart_service.initialize(llm_client, output_dir)


def generate_smart_chart(user_question: str,
                        query_data: Any,
                        additional_context: Optional[str] = None) -> Dict[str, Any]:
    """
    智能生成图表的便捷函数
    
    Args:
        user_question: 用户问题
        query_data: 查询数据
        additional_context: 额外上下文
        
    Returns:
        Dict: 生成结果
    """
    return chart_service.generate_chart(user_question, query_data, additional_context)
