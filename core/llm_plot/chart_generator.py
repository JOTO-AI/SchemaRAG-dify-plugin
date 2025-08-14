"""
Matplotlib 图表生成器
根据统一的 JSON 配置生成各种类型的图表
"""

import matplotlib
# 设置非交互式后端，避免内存问题
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
from pathlib import Path
import logging
from datetime import datetime
import gc

from .chart_schema import ChartConfig, validate_chart_config

# 配置日志
logger = logging.getLogger(__name__)

# 设置中文字体支持和现代化样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#fafafa'
plt.rcParams['axes.edgecolor'] = '#e0e0e0'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#e0e0e0'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['xtick.color'] = '#666666'
plt.rcParams['ytick.color'] = '#666666'
plt.rcParams['text.color'] = '#333333'

# 内存优化设置
plt.rcParams['figure.max_open_warning'] = 5
plt.rcParams['agg.path.chunksize'] = 10000


class ChartGenerator:
    """图表生成器主类"""
    
    def __init__(self, output_dir: str = "output/charts"):
        """
        初始化图表生成器
        
        Args:
            output_dir: 图表输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 现代化默认样式配置 - 优化尺寸以避免内存问题
        self.default_style = {
            "figure_size": (8, 5),  # 进一步减小默认尺寸
            "dpi": 80,  # 进一步减小DPI以节省内存
            "grid": True,
            "grid_alpha": 0.6,
            # 现代化配色方案 - 更加柔和且对比度适中
            "colors": ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', 
                      '#1abc9c', '#e67e22', '#34495e', '#f1c40f', '#95a5a6']
        }
    
    def generate_chart(self, config: Dict) -> str:
        """
        主分发函数：根据配置生成图表
        
        Args:
            config: 图表配置字典
            
        Returns:
            str: 生成的图表文件路径
            
        Raises:
            ValueError: 配置无效或图表类型不支持
        """
        try:
            # 强制垃圾回收和内存清理
            import gc
            gc.collect()
            
            # 确保matplotlib使用非交互式后端
            if plt.get_backend() != 'Agg':
                plt.switch_backend('Agg')
            
            # 验证配置
            chart_config = validate_chart_config(config)
            
            # 限制图表尺寸以避免内存问题
            if chart_config.style and "figure_size" in chart_config.style:
                width, height = chart_config.style["figure_size"]
                # 限制最大尺寸
                max_width, max_height = 12, 8
                if width > max_width or height > max_height:
                    chart_config.style["figure_size"] = (min(width, max_width), min(height, max_height))
                    logger.warning(f"图表尺寸过大，已调整为: {chart_config.style['figure_size']}")
            
            # 根据图表类型分发到相应的生成函数
            chart_type = chart_config.chart_type
            
            if chart_type == "bar":
                return self._generate_bar_chart(chart_config)
            elif chart_type == "line":
                return self._generate_line_chart(chart_config)
            elif chart_type == "pie":
                return self._generate_pie_chart(chart_config)
            elif chart_type == "scatter":
                return self._generate_scatter_chart(chart_config)
            elif chart_type == "histogram":
                return self._generate_histogram_chart(chart_config)
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")
                
        except Exception as e:
            logger.error(f"图表生成失败: {str(e)}")
            raise
    
    def _generate_bar_chart(self, config: ChartConfig) -> str:
        """生成柱状图"""
        try:
            # 内存预检查
            gc.collect()
            
            fig, ax = plt.subplots(figsize=self._get_figure_size(config))
            
            x_data = config.x_axis.data
            y_data = config.y_axis.data
            
            # 创建现代化柱状图
            bars = ax.bar(x_data, y_data, 
                         color=self._get_colors(config, 1)[0], 
                         alpha=0.8,
                         edgecolor='white',
                         linewidth=1.2,
                         capstyle='round')
            
            # 设置标题和标签 - 使用更现代的字体大小和间距
            ax.set_title(config.title, fontsize=16, fontweight='600', pad=25, color='#2c3e50')
            ax.set_xlabel(config.x_axis.label, fontsize=12, fontweight='500', color='#34495e')
            ax.set_ylabel(config.y_axis.label, fontsize=12, fontweight='500', color='#34495e')
            
            # 在柱子上显示数值 - 优化文本显示
            for bar, value in zip(bars, y_data):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(y_data) * 0.01,
                       f'{value}', ha='center', va='bottom', 
                       fontsize=10, fontweight='500', color='#2c3e50')
            
            # 美化坐标轴
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#bdc3c7')
            ax.spines['bottom'].set_color('#bdc3c7')
            
            # 应用样式
            self._apply_common_style(ax, config)
            
            # 保存图表
            return self._save_chart(fig, config, "bar")
            
        except Exception as e:
            # 确保图表被关闭
            plt.close('all')
            gc.collect()
            raise e
    
    def _generate_line_chart(self, config: ChartConfig) -> str:
        """生成折线图"""
        fig, ax = plt.subplots(figsize=self._get_figure_size(config))
        
        x_data = config.x_axis.data
        colors = self._get_colors(config, len(config.line_series))
        
        # 绘制现代化折线图
        for i, series in enumerate(config.line_series):
            ax.plot(x_data, series.data, 
                   marker='o', linewidth=3, markersize=8,
                   color=colors[i], label=series.label,
                   markerfacecolor='white',
                   markeredgewidth=2,
                   markeredgecolor=colors[i],
                   alpha=0.9)
        
        # 设置标题和标签
        ax.set_title(config.title, fontsize=16, fontweight='600', pad=25, color='#2c3e50')
        ax.set_xlabel(config.x_axis.label, fontsize=12, fontweight='500', color='#34495e')
        ax.set_ylabel("数值", fontsize=12, fontweight='500', color='#34495e')
        
        # 显示图例 - 现代化样式
        if len(config.line_series) > 1:
            ax.legend(loc='best', frameon=True, shadow=False, 
                     fancybox=True, framealpha=0.9,
                     edgecolor='#bdc3c7', facecolor='white')
        
        # 美化坐标轴
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#bdc3c7')
        ax.spines['bottom'].set_color('#bdc3c7')
        
        # 应用样式
        self._apply_common_style(ax, config)
        
        return self._save_chart(fig, config, "line")
    
    def _generate_pie_chart(self, config: ChartConfig) -> str:
        """生成饼图"""
        fig, ax = plt.subplots(figsize=self._get_figure_size(config))
        
        labels = config.pie_data.labels
        values = config.pie_data.values
        colors = self._get_colors(config, len(labels))
        
        # 创建现代化饼图
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors,
            autopct='%1.1f%%', startangle=90,
            textprops={'fontsize': 11, 'fontweight': '500'},
            explode=[0.05] * len(labels),  # 轻微分离效果
            shadow=False,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}
        )
        
        # 美化文本
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('600')
            autotext.set_fontsize(10)
        
        for text in texts:
            text.set_fontweight('500')
            text.set_color('#2c3e50')
        
        # 设置标题
        ax.set_title(config.title, fontsize=16, fontweight='600', pad=25, color='#2c3e50')
        
        # 确保饼图是圆形
        ax.axis('equal')
        
        return self._save_chart(fig, config, "pie")
    
    def _generate_scatter_chart(self, config: ChartConfig) -> str:
        """生成散点图"""
        fig, ax = plt.subplots(figsize=self._get_figure_size(config))
        
        x_data = config.x_axis.data
        y_data = config.y_axis.data
        
        # 创建现代化散点图
        scatter = ax.scatter(x_data, y_data, 
                            c=self._get_colors(config, 1)[0], 
                            alpha=0.7, s=80,
                            edgecolors='white',
                            linewidth=1.5)
        
        # 设置标题和标签
        ax.set_title(config.title, fontsize=16, fontweight='600', pad=25, color='#2c3e50')
        ax.set_xlabel(config.x_axis.label, fontsize=12, fontweight='500', color='#34495e')
        ax.set_ylabel(config.y_axis.label, fontsize=12, fontweight='500', color='#34495e')
        
        # 美化坐标轴
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#bdc3c7')
        ax.spines['bottom'].set_color('#bdc3c7')
        
        # 应用样式
        self._apply_common_style(ax, config)
        
        return self._save_chart(fig, config, "scatter")
    
    def _generate_histogram_chart(self, config: ChartConfig) -> str:
        """生成直方图"""
        fig, ax = plt.subplots(figsize=self._get_figure_size(config))
        
        data = config.y_axis.data
        
        # 创建现代化直方图
        n, bins, patches = ax.hist(data, bins=20, 
                                  color=self._get_colors(config, 1)[0], 
                                  alpha=0.7, 
                                  edgecolor='white',
                                  linewidth=1.2)
        
        # 设置标题和标签
        ax.set_title(config.title, fontsize=16, fontweight='600', pad=25, color='#2c3e50')
        ax.set_xlabel(config.x_axis.label, fontsize=12, fontweight='500', color='#34495e')
        ax.set_ylabel("频数", fontsize=12, fontweight='500', color='#34495e')
        
        # 美化坐标轴
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#bdc3c7')
        ax.spines['bottom'].set_color('#bdc3c7')
        
        # 应用样式
        self._apply_common_style(ax, config)
        
        return self._save_chart(fig, config, "histogram")
    
    def _apply_common_style(self, ax, config: ChartConfig):
        """应用现代化通用样式"""
        style = config.style or {}
        
        # 网格样式 - 更加优雅
        if style.get("grid", self.default_style["grid"]):
            ax.grid(True, alpha=style.get("grid_alpha", self.default_style["grid_alpha"]), 
                   linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)  # 网格在背后
        
        # 设置坐标轴样式 - 更加现代
        ax.tick_params(axis='both', which='major', labelsize=10, 
                      colors='#666666', length=4, width=0.8)
        ax.tick_params(axis='both', which='minor', length=2, width=0.5)
        
        # 设置边距
        ax.margins(x=0.02, y=0.05)
        
        # 紧凑布局
        plt.tight_layout(pad=2.0)
    
    def _get_figure_size(self, config: ChartConfig) -> Tuple[int, int]:
        """获取图表尺寸"""
        if config.style and "figure_size" in config.style:
            return config.style["figure_size"]
        return self.default_style["figure_size"]
    
    def _get_colors(self, config: ChartConfig, count: int) -> List[str]:
        """获取颜色列表"""
        if config.style and "colors" in config.style:
            colors = config.style["colors"]
        else:
            colors = self.default_style["colors"]
        
        # 如果需要的颜色数量超过可用颜色，循环使用
        return [colors[i % len(colors)] for i in range(count)]
    
    def _save_chart(self, fig, config: ChartConfig, chart_type: str) -> str:
        """保存图表到文件"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{chart_type}_{timestamp}.png"
        filepath = self.output_dir / filename
        
        # 获取DPI并限制最大值以避免内存问题
        dpi = config.style.get("dpi", self.default_style["dpi"]) if config.style else self.default_style["dpi"]
        dpi = min(dpi, 100)  # 限制最大DPI为100
        
        try:
            # 保存图表
            fig.savefig(filepath, dpi=dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none',
                       format='png')
        finally:
            # 确保释放图表内存
            plt.close(fig)
            # 强制垃圾回收
            import gc
            gc.collect()
        
        logger.info(f"图表已保存到: {filepath}")
        return str(filepath)


# 便捷函数
def generate_chart(config: Dict, output_dir: str = "output/charts") -> str:
    """
    便捷的图表生成函数
    
    Args:
        config: 图表配置字典
        output_dir: 输出目录
        
    Returns:
        str: 生成的图表文件路径
    """
    generator = ChartGenerator(output_dir)
    return generator.generate_chart(config)
